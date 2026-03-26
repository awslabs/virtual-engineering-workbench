from datetime import datetime, timezone

import semver

from app.packaging.domain.commands.component import release_component_version_command
from app.packaging.domain.events.component import (
    component_version_release_completed,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import (
    component_version_query_service,
    recipe_version_query_service,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __validate_dependencies(
    component_version_entity: component_version.ComponentVersion,
):
    if component_version_entity.componentVersionDependencies:
        for component_version_dependency in component_version_entity.componentVersionDependencies:
            if semver.Version.parse(component_version_dependency.componentVersionName).prerelease:
                raise domain_exception.DomainException(
                    f"Can not release the component version {component_version_entity.componentVersionName} "
                    "because not all its dependencies have been released yet."
                )


def __update_downstream_dependencies(
    update_component_version_name: str,
    component_version_entity: component_version.ComponentVersion,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    uow: unit_of_work.UnitOfWork,
):
    if component_version_entity.associatedComponentsVersions is not None:
        for associated_component_version in component_version_entity.associatedComponentsVersions:
            associated_component_version_entity = component_version_qry_srv.get_component_version(
                associated_component_version.componentId,
                associated_component_version.componentVersionId,
            )

            if associated_component_version_entity is None:
                raise domain_exception.DomainException(
                    f"Version {associated_component_version.componentVersionId} of component "
                    f"{associated_component_version.componentId} does not exist."
                )

            for dependency in associated_component_version_entity.componentVersionDependencies:
                if dependency.componentVersionId == component_version_entity.componentVersionId:
                    dependency.componentVersionName = update_component_version_name

            with uow:
                uow.get_repository(
                    component_version.ComponentVersionPrimaryKey,
                    component_version.ComponentVersion,
                ).update_entity(
                    component_version.ComponentVersionPrimaryKey(
                        componentId=associated_component_version.componentId,
                        componentVersionId=associated_component_version.componentVersionId,
                    ),
                    associated_component_version_entity,
                )
                uow.commit()


def __update_recipe_references(
    updated_component_version_name: str,
    component_version_entity: component_version.ComponentVersion,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    uow: unit_of_work.UnitOfWork,
):
    for recipe in component_version_entity.associatedRecipesVersions:
        recipe_version_entity = recipe_version_qry_srv.get_recipe_version(recipe.recipeId, recipe.recipeVersionId)

        if recipe_version_entity is None:
            raise domain_exception.DomainException(
                f"Version {recipe.recipeVersionId} of recipe {recipe.recipeId} does not exist."
            )
        for recipe_component in recipe_version_entity.recipeComponentsVersions:
            if recipe_component.componentVersionId == component_version_entity.componentVersionId:
                if recipe_component.componentVersionName != updated_component_version_name:
                    recipe_component.componentVersionName = updated_component_version_name
                    with uow:
                        uow.get_repository(
                            recipe_version.RecipeVersionPrimaryKey,
                            recipe_version.RecipeVersion,
                        ).update_entity(
                            recipe_version.RecipeVersionPrimaryKey(
                                recipeId=recipe_version_entity.recipeId,
                                recipeVersionId=recipe_version_entity.recipeVersionId,
                            ),
                            recipe_version_entity,
                        )
                        uow.commit()


def handle(
    command: release_component_version_command.ReleaseComponentVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
):
    component_version_entity = component_version_qry_srv.get_component_version(
        command.componentId.value, command.componentVersionId.value
    )

    if component_version_entity is None:
        raise domain_exception.DomainException(
            f"Version {command.componentVersionId.value} of component {command.componentId.value} does not exist."
        )

    try:
        component_version_name = component_version_entity.componentVersionName
        component_version_parsed = semver.Version.parse(component_version_name)
    except:
        raise domain_exception.DomainException(f"Version {component_version_name} is not a valid SemVer string.")

    if component_version_parsed.prerelease is None:
        raise domain_exception.DomainException(
            f"Can not release an already released component version ({component_version_name}) - only release candidates are allowed."
        )

    if component_version_entity.status != component_version.ComponentVersionStatus.Validated:
        raise domain_exception.DomainException(
            f"Version {component_version_name} of component {command.componentId.value} can't be released while in {component_version_entity.status} status: "
            f"only {component_version.ComponentVersionStatus.Validated} is accepted."
        )

    __validate_dependencies(component_version_entity)

    final_component_version_name = str(component_version_parsed.finalize_version())
    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(
            component_version.ComponentVersionPrimaryKey,
            component_version.ComponentVersion,
        ).update_attributes(
            component_version.ComponentVersionPrimaryKey(
                componentId=command.componentId.value,
                componentVersionId=command.componentVersionId.value,
            ),
            lastUpdateDate=current_time,
            lastUpdateBy=command.lastUpdatedBy.value,
            componentVersionName=final_component_version_name,
            status=component_version.ComponentVersionStatus.Released,
        )
        uow.commit()
    __update_downstream_dependencies(
        update_component_version_name=final_component_version_name,
        component_version_entity=component_version_entity,
        component_version_qry_srv=component_version_qry_srv,
        uow=uow,
    )
    if component_version_entity.associatedRecipesVersions:
        __update_recipe_references(
            updated_component_version_name=final_component_version_name,
            component_version_entity=component_version_entity,
            recipe_version_qry_srv=recipe_version_qry_srv,
            uow=uow,
        )

    message_bus.publish(
        component_version_release_completed.ComponentVersionReleaseCompleted(
            component_id=command.componentId.value,
            component_version_id=command.componentVersionId.value,
            component_version_dependencies=component_version_entity.componentVersionDependencies,
        )
    )
