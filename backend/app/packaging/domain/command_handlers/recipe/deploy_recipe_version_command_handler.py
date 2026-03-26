import logging
import os.path

import semver
from jinja2 import Environment, FileSystemLoader

from app.packaging.domain.commands.recipe import deploy_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_published
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe, recipe_version
from app.packaging.domain.ports import (
    component_version_definition_service,
    component_version_query_service,
    component_version_service,
    recipe_query_service,
    recipe_version_service,
)
from app.packaging.domain.value_objects.component import component_build_version_arn_value_object
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_arn_value_object,
    recipe_version_components_versions_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __update_attributes(
    command: deploy_recipe_version_command.DeployRecipeVersionCommand,
    uow: unit_of_work.UnitOfWork,
    status: recipe_version.RecipeVersionStatus,
    recipeVersionComponentArn: (
        component_build_version_arn_value_object.ComponentBuildVersionArnValueObject | None
    ) = None,
    recipeVersionArn: recipe_version_arn_value_object.RecipeVersionArnValueObject | None = None,
):
    with uow:
        uow.get_repository(
            recipe_version.RecipeVersionPrimaryKey,
            recipe_version.RecipeVersion,
        ).update_attributes(
            recipe_version.RecipeVersionPrimaryKey(
                recipeId=command.recipeId.value,
                recipeVersionId=command.recipeVersionId.value,
            ),
            recipeVersionArn=recipeVersionArn,
            recipeVersionComponentArn=recipeVersionComponentArn,
            status=status,
        )
        uow.commit()


def __generate_nested_component_definition(
    component_arns: list[component_build_version_arn_value_object.ComponentBuildVersionArnValueObject],
):
    if None in component_arns:
        raise domain_exception.DomainException("Component ARN can not be None.")
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))  # nosec B701
    template = env.get_template("recipe.yaml.j2")
    rendered_template = template.render(component_arns=component_arns)
    return rendered_template.encode("utf-8")


def __create_recipe_component_list(
    component_version_query_service: component_version_query_service.ComponentVersionQueryService,
    components: recipe_version_components_versions_value_object.RecipeVersionComponentsVersionsValueObject,
    component_version_service: component_version_service.ComponentVersionService,
    recipe_component_definition_service: component_version_definition_service.ComponentVersionDefinitionService,
    recipe_entity: recipe.Recipe,
    recipe_component_version_name: str,
    recipe_version_build_arn: str | None,
) -> list[str]:
    try:
        component_arns = list()
        sorted_components = sorted(components.value, key=lambda x: x.order)
        for item in sorted_components:
            component_version = component_version_query_service.get_component_version(
                component_id=item.componentId,
                version_id=item.componentVersionId,
            )
            if component_version is None:
                raise domain_exception.DomainException(
                    f"Component version {item.componentVersionId} for {item.componentId} not found."
                )
            component_arns.append(component_version.componentBuildVersionArn)
        component_definition = __generate_nested_component_definition(list(dict.fromkeys(component_arns)))
        component_name = recipe_entity.recipeId
        component_s3_uri = recipe_component_definition_service.upload(
            component_id=component_name,
            component_version=recipe_component_version_name,
            component_definition=component_definition,
        )
        component_version_name = str(semver.Version.parse(recipe_component_version_name).finalize_version())
        # If the recipe version has been already created also the component exists and must be deleted
        if recipe_version_build_arn:
            component_version_build_arn = component_version_service.get_build_arn(
                name=component_name, version=component_version_name
            )

            component_version_service.delete(component_build_version_arn=component_version_build_arn)

        component_version_build_arn = component_version_service.create(
            name=component_name,
            version=component_version_name,
            s3_component_uri=component_s3_uri,
            platform=recipe_entity.recipePlatform,
            supported_os_versions=[recipe_entity.recipeOsVersion],
            description=f"Nested component for recipe: {recipe_entity.recipeId} and version: {recipe_component_version_name}.",
        )
        return [component_version_build_arn]

    except Exception as e:
        raise domain_exception.DomainException("Failed to create recipe component list.") from e


def handle(
    command: deploy_recipe_version_command.DeployRecipeVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    recipe_version_service: recipe_version_service.RecipeVersionService,
    recipe_query_service: recipe_query_service.RecipeQueryService,
    component_version_query_service: component_version_query_service.ComponentVersionQueryService,
    component_version_service: component_version_service.ComponentVersionService,
    recipe_component_definition_service: component_version_definition_service.ComponentVersionDefinitionService,
    logger: logging.Logger,
):
    try:
        recipe_entity = recipe_query_service.get_recipe(
            project_id=command.projectId.value, recipe_id=command.recipeId.value
        )
        if recipe_entity is None:
            raise domain_exception.DomainException(f"Recipe {command.recipeId.value} can not be found.")
        recipe_version_name = command.recipeVersionName.value
        recipe_version_name_parsed = semver.Version.parse(recipe_version_name)
        recipe_version_name_upstream = str(recipe_version_name_parsed.finalize_version())
        recipe_version_build_arn = recipe_version_service.get_build_arn(
            name=command.recipeId.value, version=recipe_version_name_upstream
        )
        if recipe_version_build_arn:
            if recipe_version_name_parsed.prerelease:
                recipe_version_service.delete(recipe_version_arn=recipe_version_build_arn)
            else:
                raise domain_exception.DomainException(
                    f"Recipe version {recipe_version_name} of {command.recipeId.value} already exists."
                )

        recipe_component_arns = __create_recipe_component_list(
            component_version_query_service=component_version_query_service,
            components=command.components,
            component_version_service=component_version_service,
            recipe_component_definition_service=recipe_component_definition_service,
            recipe_entity=recipe_entity,
            recipe_component_version_name=recipe_version_name,
            recipe_version_build_arn=recipe_version_build_arn,
        )

        recipe_version_build_arn = recipe_version_service.create(
            name=command.recipeId.value,
            version=f"{recipe_version_name_upstream}",
            component_arns=recipe_component_arns,
            parent_image=command.parentImageUpstreamId.value,
            volume_size=int(command.recipeVersionVolumeSize.value),
            description=recipe_entity.recipeDescription,
        )

        __update_attributes(
            command=command,
            uow=uow,
            status=recipe_version.RecipeVersionStatus.Created,
            recipeVersionComponentArn=recipe_component_arns[0],
            recipeVersionArn=recipe_version_build_arn,
        )

        message_bus.publish(
            recipe_version_published.RecipeVersionPublished(
                projectId=command.projectId.value,
                recipe_id=command.recipeId.value,
                recipe_version_id=command.recipeVersionId.value,
            )
        )
    except domain_exception.DomainException:
        logger.exception(
            f"Recipe version {command.recipeVersionId.value} of {command.recipeId.value} failed to create."
        )
        __update_attributes(command, uow, recipe_version.RecipeVersionStatus.Failed)
        raise
    except Exception as e:
        error_msg = f"Recipe version {command.recipeVersionId.value} of {command.recipeId.value} failed to create."
        logger.exception(error_msg)
        __update_attributes(command, uow, recipe_version.RecipeVersionStatus.Failed)
        raise domain_exception.DomainException(error_msg) from e
