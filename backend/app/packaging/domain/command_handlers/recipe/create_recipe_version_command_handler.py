from collections import Counter
from datetime import datetime, timezone
from enum import StrEnum

import boto3
import semver

from app.packaging.domain.commands.recipe import create_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_creation_started
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
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

INITIAL_VERSION = "1.0.0-rc.1"


class SystemConfigurationMappingAttributes(StrEnum):
    AMI_SSM_PARAM_NAME = "ami_ssm_param_name"


def __calculate_new_version_name(
    command: create_recipe_version_command.CreateRecipeVersionCommand,
    latest_recipe_version_name: str | None,
) -> str:
    new_recipe_version_name = INITIAL_VERSION
    if latest_recipe_version_name:
        try:
            latest_recipe_version_parsed = semver.Version.parse(latest_recipe_version_name)
        except:
            raise domain_exception.DomainException(
                f"Version {latest_recipe_version_name} is not a valid SemVer string."
            )

        if command.recipeVersionReleaseType.value == recipe_version.RecipeVersionReleaseType.Major:
            new_recipe_version_name = str(latest_recipe_version_parsed.bump_major().bump_prerelease())
        elif command.recipeVersionReleaseType.value == recipe_version.RecipeVersionReleaseType.Minor:
            new_recipe_version_name = str(latest_recipe_version_parsed.bump_minor().bump_prerelease())
        elif command.recipeVersionReleaseType.value == recipe_version.RecipeVersionReleaseType.Patch:
            new_recipe_version_name = str(latest_recipe_version_parsed.bump_patch().bump_prerelease())

    return new_recipe_version_name


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


def __validate_component_duplication(
    recipe_component_versions: list[component_version_entry.ComponentVersionEntry],
    mandatory_component_versions: list[component_version_entry.ComponentVersionEntry],
) -> None:
    component_counter = Counter([component_version.componentId for component_version in recipe_component_versions])

    if not (duplicate_component_ids := {id for id, count in component_counter.items() if count > 1}):
        return

    mandatory_components_map = {component.componentId: component for component in recipe_component_versions}

    prepended_mandatory_ids = {
        mc.componentId
        for mc in mandatory_component_versions
        if mc.componentId in duplicate_component_ids
        and mc.position == component_version_entry.ComponentVersionEntryPosition.Prepend
    }
    appended_mandatory_ids = {
        mc.componentId
        for mc in mandatory_component_versions
        if mc.componentId in duplicate_component_ids
        and mc.position == component_version_entry.ComponentVersionEntryPosition.Append
    }

    exception_message = [
        f"Recipe version contains duplicate components: {sorted([mandatory_components_map.get(c_id).componentName for c_id in duplicate_component_ids])}.",
        (
            f"Components {sorted([mandatory_components_map.get(mc_id).componentName for mc_id in prepended_mandatory_ids])} are prepended automatically and shouldn't be re-included."
            if prepended_mandatory_ids
            else None
        ),
        (
            f"Components {sorted([mandatory_components_map.get(mc_id).componentName for mc_id in appended_mandatory_ids])} are appended automatically and shouldn't be re-included."
            if appended_mandatory_ids
            else None
        ),
    ]

    raise domain_exception.DomainException(" ".join([e for e in exception_message if e]))


def __extend_component_versions_list(
    existing: list[component_version_entry.ComponentVersionEntry],
    new: list[component_version_entry.ComponentVersionEntry],
):
    for nc in sorted(new, key=lambda x: x.order):
        nc.order = len(existing) + 1
        existing.append(nc)


def __get_recipe_entity(
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    project_id: str,
    recipe_id: str,
) -> recipe.Recipe:
    recipe_entity = recipe_qry_srv.get_recipe(project_id=project_id, recipe_id=recipe_id)

    if recipe_entity is None:
        raise domain_exception.DomainException(f"Recipe {recipe_id} can not be found.")
    if recipe_entity.status is recipe.RecipeStatus.Archived:
        raise domain_exception.DomainException(f"Recipe {recipe_id} is in {recipe.RecipeStatus.Archived} status.")

    return recipe_entity


def __process_mandatory_components(
    mandatory_components_list_qry_srv: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
    recipe_entity: recipe.Recipe,
):
    mandatory_component_versions = []
    prepended_mandatory_components = []
    appended_mandatory_components = []

    if mandatory_components_list := mandatory_components_list_qry_srv.get_mandatory_components_list(
        architecture=recipe_entity.recipeArchitecture,
        os=recipe_entity.recipeOsVersion,
        platform=recipe_entity.recipePlatform,
    ):
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


def __validate_user_components(
    command: create_recipe_version_command.CreateRecipeVersionCommand,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
):
    for user_component_version_entry in command.recipeComponentsVersions.value:
        component_version_entity = component_version_qry_srv.get_component_version(
            component_id=user_component_version_entry.componentId,
            version_id=user_component_version_entry.componentVersionId,
        )

        _check_component_version_entity(
            component_id=user_component_version_entry.componentId,
            component_version_id=user_component_version_entry.componentVersionId,
            component_version_entity=component_version_entity,
        )


def __assemble_recipe_components(
    prepended_mandatory_components,
    user_components,
    appended_mandatory_components,
):
    recipe_component_versions = []

    __extend_component_versions_list(recipe_component_versions, prepended_mandatory_components)
    __extend_component_versions_list(recipe_component_versions, user_components)
    __extend_component_versions_list(recipe_component_versions, appended_mandatory_components)

    return recipe_component_versions


def handle(
    command: create_recipe_version_command.CreateRecipeVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    parameter_srv: parameter_service.ParameterDefinitionService,
    mandatory_components_list_qry_srv: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
    system_configuration_mapping: dict,
):
    recipe_entity = __get_recipe_entity(
        recipe_qry_srv=recipe_qry_srv,
        project_id=command.projectId.value,
        recipe_id=command.recipeId.value,
    )

    latest_recipe_version_name = recipe_version_qry_srv.get_latest_recipe_version_name(command.recipeId.value)
    new_recipe_version_name = __calculate_new_version_name(command, latest_recipe_version_name)

    try:
        parent_image_upstream_id = recipe_version_parent_image_upstream_id_value_object.from_str(
            parameter_srv.get_parameter_value(
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

    (
        mandatory_component_versions,
        prepended_mandatory_components,
        appended_mandatory_components,
    ) = __process_mandatory_components(mandatory_components_list_qry_srv, recipe_entity)

    __validate_user_components(command, component_version_qry_srv)

    recipe_component_versions = __assemble_recipe_components(
        prepended_mandatory_components,
        command.recipeComponentsVersions.value,
        appended_mandatory_components,
    )

    __validate_component_duplication(
        recipe_component_versions,
        mandatory_component_versions,
    )

    selected_integrations = [rvi.value for rvi in command.recipeVersionIntegrations or []]

    current_time = datetime.now(timezone.utc).isoformat()
    recipe_version_entity = recipe_version.RecipeVersion(
        recipeId=command.recipeId.value,
        recipeVersionName=recipe_version_name_value_object.from_str(new_recipe_version_name).value,
        parentImageUpstreamId=parent_image_upstream_id,
        recipeComponentsVersions=recipe_version_components_versions_value_object.from_list(
            recipe_component_versions
        ).value,
        recipeName=recipe_entity.recipeName,
        recipeVersionDescription=command.recipeVersionDescription.value,
        recipeVersionVolumeSize=command.recipeVersionVolumeSize.value,
        recipeVersionIntegrations=selected_integrations,
        status=recipe_version.RecipeVersionStatus.Creating,
        createDate=current_time,
        lastUpdateDate=current_time,
        createdBy=command.createdBy.value,
        lastUpdatedBy=command.createdBy.value,
    )

    with uow:
        uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).add(
            recipe_version_entity
        )
        uow.commit()

    message_bus.publish(
        recipe_version_creation_started.RecipeVersionCreationStarted(
            project_id=command.projectId.value,
            recipe_id=command.recipeId.value,
            recipe_version_id=recipe_version_entity.recipeVersionId,
            parent_image_upstream_id=parent_image_upstream_id,
            recipe_component_versions=recipe_version_components_versions_value_object.from_list(
                recipe_component_versions
            ).value,
            recipe_version_name=recipe_version_name_value_object.from_str(new_recipe_version_name).value,
            recipe_version_volume_size=recipe_version_entity.recipeVersionVolumeSize,
        )
    )
