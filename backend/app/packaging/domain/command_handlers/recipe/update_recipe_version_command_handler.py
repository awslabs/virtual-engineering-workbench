from datetime import datetime, timezone
from enum import StrEnum

import boto3
import semver

from app.packaging.domain.commands.recipe import update_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_update_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe, recipe_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.ports import (
    component_version_query_service,
    mandatory_components_list_query_service,
    parameter_service,
    recipe_query_service,
    recipe_version_query_service,
)
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_components_versions_value_object,
    recipe_version_name_value_object,
    recipe_version_parent_image_upstream_id_value_object,
    recipe_version_volume_size_value_object,
)
from app.shared.adapters.message_bus.message_bus import MessageBus
from app.shared.adapters.unit_of_work_v2.unit_of_work import UnitOfWork


class SystemConfigurationMappingAttributes(StrEnum):
    AMI_SSM_PARAM_NAME = "ami_ssm_param_name"


def _check_component_version_entity(
    component_id: str,
    component_version_id: str,
    component_version_entity: component_version.ComponentVersion | None,
) -> None:
    if component_version_entity is None:
        raise domain_exception.DomainException(
            f"Version {component_version_id} of component {component_id} does not exist."
        )

    acceptable_component_version_states = [
        component_version.ComponentVersionStatus.Released,
        component_version.ComponentVersionStatus.Validated,
    ]

    if component_version_entity.status not in acceptable_component_version_states:
        raise domain_exception.DomainException(
            f"Version {component_version_entity.componentVersionName} of component {component_id} "
            f"can't be included in this recipe version while in {component_version_entity.status} status: "
            f"only {component_version.ComponentVersionStatus.Released} and "
            f"{component_version.ComponentVersionStatus.Validated} states are accepted."
        )


def __get_recipe_version_entity(
    command: update_recipe_version_command.UpdateRecipeVersionCommand,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService,
):
    recipe_version_entity = recipe_version_query_service.get_recipe_version(
        recipe_id=command.recipeId.value, version_id=command.recipeVersionId.value
    )

    if recipe_version_entity is None:
        raise domain_exception.DomainException(
            f"No recipe version {command.recipeVersionId.value} found for {command.recipeId.value}"
        )

    return recipe_version_entity


def __separate_mandatory_components(mandatory_components_list):
    mandatory_component_versions = []
    prepended_mandatory_components = []
    appended_mandatory_components = []

    if mandatory_components_list:
        mandatory_component_versions = mandatory_components_list.mandatoryComponentsVersions

        for comp in mandatory_component_versions:
            if comp.componentVersionType is None:
                comp.componentVersionType = component_version_entry.ComponentVersionEntryType.Helper
            if comp.position == component_version_entry.ComponentVersionEntryPosition.Prepend:
                prepended_mandatory_components.append(comp)
            elif comp.position == component_version_entry.ComponentVersionEntryPosition.Append:
                appended_mandatory_components.append(comp)

    return (
        mandatory_component_versions,
        prepended_mandatory_components,
        appended_mandatory_components,
    )


def __filter_and_validate_user_components(
    command: update_recipe_version_command.UpdateRecipeVersionCommand,
    mandatory_component_ids: list,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
):
    user_component_versions = [
        component_version
        for component_version in command.recipeComponentsVersions.value
        if component_version.componentId not in mandatory_component_ids
    ]

    user_component_versions = sorted(user_component_versions, key=lambda comp: comp.order)

    for idx, comp in enumerate(user_component_versions):
        comp.order = idx + 1

    for comp in user_component_versions:
        component_version_entity = component_version_qry_srv.get_component_version(
            component_id=comp.componentId,
            version_id=comp.componentVersionId,
        )

        _check_component_version_entity(
            component_id=comp.componentId,
            component_version_id=comp.componentVersionId,
            component_version_entity=component_version_entity,
        )

    return user_component_versions


def __assemble_positioned_components(
    prepended_mandatory_components,
    user_component_versions,
    appended_mandatory_components,
):
    recipe_component_versions = []

    for idx, comp in enumerate(prepended_mandatory_components, start=1):
        comp.order = idx
        recipe_component_versions.append(comp)

    offset = len(prepended_mandatory_components)
    for comp in user_component_versions:
        comp.order += offset
        recipe_component_versions.append(comp)

    offset = len(prepended_mandatory_components) + len(user_component_versions)
    for idx, comp in enumerate(appended_mandatory_components, start=1):
        comp.order = offset + idx
        recipe_component_versions.append(comp)

    return recipe_component_versions


def __get_recipe_component_versions(
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    mandatory_components_list_qry_srv: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
    recipe_entity: recipe.Recipe,
    command: update_recipe_version_command.UpdateRecipeVersionCommand,
):
    mandatory_components_list = mandatory_components_list_qry_srv.get_mandatory_components_list(
        architecture=recipe_entity.recipeArchitecture,
        os=recipe_entity.recipeOsVersion,
        platform=recipe_entity.recipePlatform,
    )

    (
        mandatory_component_versions,
        prepended_mandatory_components,
        appended_mandatory_components,
    ) = __separate_mandatory_components(mandatory_components_list)

    mandatory_component_ids = [comp.componentId for comp in mandatory_component_versions]

    user_component_versions = __filter_and_validate_user_components(
        command, mandatory_component_ids, component_version_qry_srv
    )

    recipe_component_versions = __assemble_positioned_components(
        prepended_mandatory_components,
        user_component_versions,
        appended_mandatory_components,
    )

    return recipe_component_versions


def _get_parent_image_upstream_id(
    parameter_qry_srv: parameter_service.ParameterDefinitionService,
    system_configuration_mapping: dict,
    recipe_entity: recipe.Recipe,
):
    try:
        parent_image_upstream_id = recipe_version_parent_image_upstream_id_value_object.from_str(
            parameter_qry_srv.get_parameter_value(
                system_configuration_mapping.get(recipe_entity.recipePlatform)
                .get(recipe_entity.recipeArchitecture)
                .get(recipe_entity.recipeOsVersion)
                .get(SystemConfigurationMappingAttributes.AMI_SSM_PARAM_NAME.value)
            )
        ).value
    except boto3.client("ssm").exceptions.ParameterNotFound:
        raise domain_exception.DomainException(
            f"Parameter {SystemConfigurationMappingAttributes.AMI_SSM_PARAM_NAME.value} not found."
        )
    return parent_image_upstream_id


def handle(
    command: update_recipe_version_command.UpdateRecipeVersionCommand,
    uow: UnitOfWork,
    message_bus: MessageBus,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService,
    recipe_qry_service: recipe_query_service.RecipeQueryService,
    parameter_qry_srv: parameter_service.ParameterDefinitionService,
    mandatory_components_list_qry_srv: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
    system_configuration_mapping: dict,
):

    recipe_version_entity = __get_recipe_version_entity(command, recipe_version_query_service)
    recipe_version_name = recipe_version_entity.recipeVersionName

    try:
        recipe_version_parsed = semver.Version.parse(recipe_version_name)
    except Exception:
        raise domain_exception.DomainException(f"Not a semantic version {recipe_version_name}")

    if recipe_version_parsed.prerelease is None:
        raise domain_exception.DomainException(
            f"Can not update an already Generally Available recipe version. {recipe_version_name}"
        )

    update_current_recipe_version = str(recipe_version_parsed.bump_prerelease())

    try:
        recipe_entity = recipe_qry_service.get_recipe(
            project_id=command.projectId.value, recipe_id=command.recipeId.value
        )
    except Exception as e:
        raise domain_exception.DomainException(f"Recipe {command.recipeId.value} not found.") from e

    parent_image_upstream_id = _get_parent_image_upstream_id(
        parameter_qry_srv, system_configuration_mapping, recipe_entity
    )

    recipe_component_versions = __get_recipe_component_versions(
        component_version_qry_srv,
        mandatory_components_list_qry_srv,
        recipe_entity,
        command,
    )

    component_ids = [component_version.componentId for component_version in recipe_component_versions]
    duplicate_component_ids = list(
        set([component_id for component_id in component_ids if component_ids.count(component_id) > 1])
    )
    if duplicate_component_ids:
        raise domain_exception.DomainException(
            f"Recipe version contains duplicate components: {sorted(duplicate_component_ids)}."
        )

    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).update_attributes(
            recipe_version.RecipeVersionPrimaryKey(
                recipeId=command.recipeId.value,
                recipeVersionId=command.recipeVersionId.value,
            ),
            parentImageUpstreamId=parent_image_upstream_id,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry.parse_obj(component_version).dict()
                for component_version in recipe_component_versions
            ],
            recipeVersionName=recipe_version_name_value_object.from_str(update_current_recipe_version).value,
            recipeVersionDescription=command.recipeVersionDescription.value,
            recipeVersionVolumeSize=command.recipeVersionVolumeSize.value,
            recipeVersionIntegrations=[rvi.value for rvi in command.recipeVersionIntegrations or []],
            status=recipe_version.RecipeVersionStatus.Updating,
            lastUpdateDate=current_time,
            lastUpdatedBy=command.lastUpdatedBy.value,
        )
        uow.commit()

    message_bus.publish(
        recipe_version_update_started.RecipeVersionUpdateStarted(
            project_id=command.projectId.value,
            recipe_id=command.recipeId.value,
            recipe_version_id=command.recipeVersionId.value,
            parent_image_upstream_id=recipe_version_entity.parentImageUpstreamId,
            previous_recipe_components_versions=recipe_version_entity.recipeComponentsVersions,
            recipe_components_versions=recipe_version_components_versions_value_object.from_list(
                recipe_component_versions
            ).value,
            recipe_version_name=recipe_version_name_value_object.from_str(update_current_recipe_version).value,
            recipe_version_volume_size=recipe_version_volume_size_value_object.from_str(
                recipe_version_entity.recipeVersionVolumeSize
            ).value,
        )
    )
