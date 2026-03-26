from collections import Counter
from datetime import datetime, timezone
from typing import List

import semver

from app.packaging.domain.commands.recipe import create_automated_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_creation_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe, recipe_version
from app.packaging.domain.model.recipe.recipe_version import (
    RecipeVersionReleaseType,
)
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
    ComponentVersionEntryPosition,
    ComponentVersionEntryType,
)
from app.packaging.domain.ports import (
    component_query_service,
    component_version_query_service,
    mandatory_components_list_query_service,
    recipe_query_service,
    recipe_version_query_service,
)
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_name_value_object,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

INITIAL_VERSION = "1.0.0-rc.1"


def _find_last_released_version(
    recipe_versions: List[recipe_version.RecipeVersion], recipe_id: str
) -> recipe_version.RecipeVersion:
    last_released_version = None
    for version in recipe_versions:
        if version.status == recipe_version.RecipeVersionStatus.Released:
            if last_released_version is None or semver.Version.parse(version.recipeVersionName) > semver.Version.parse(
                last_released_version.recipeVersionName
            ):
                last_released_version = version

    if not last_released_version:
        raise domain_exception.DomainException(f"No released recipe version found for recipe {recipe_id}")

    return last_released_version


def __extend_component_versions_list(
    existing: list[ComponentVersionEntry],
    new: list[ComponentVersionEntry],
):
    for nc in sorted(new, key=lambda x: x.order):
        nc.order = len(existing) + 1
        existing.append(nc)


def __validate_component_duplication(
    recipe_component_versions: list[ComponentVersionEntry],
    mandatory_component_versions: list[ComponentVersionEntry],
) -> None:
    component_counter = Counter([component_version.componentId for component_version in recipe_component_versions])

    if not (duplicate_component_ids := {id for id, count in component_counter.items() if count > 1}):
        return

    mandatory_components_map = {component.componentId: component for component in recipe_component_versions}

    prepended_mandatory_ids = {
        mc.componentId
        for mc in mandatory_component_versions
        if mc.componentId in duplicate_component_ids and mc.position == ComponentVersionEntryPosition.Prepend
    }
    appended_mandatory_ids = {
        mc.componentId
        for mc in mandatory_component_versions
        if mc.componentId in duplicate_component_ids and mc.position == ComponentVersionEntryPosition.Append
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
                comp.componentVersionType = ComponentVersionEntryType.Helper
            if comp.position == ComponentVersionEntryPosition.Prepend:
                prepended_mandatory_components.append(comp)
            elif comp.position == ComponentVersionEntryPosition.Append:
                appended_mandatory_components.append(comp)

    return (
        mandatory_component_versions,
        prepended_mandatory_components,
        appended_mandatory_components,
    )


def __calculate_new_version_name(
    command: create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand,
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

        if command.recipeVersionReleaseType.value == RecipeVersionReleaseType.Major:
            new_recipe_version_name = str(latest_recipe_version_parsed.bump_major().bump_prerelease())
        elif command.recipeVersionReleaseType.value == RecipeVersionReleaseType.Minor:
            new_recipe_version_name = str(latest_recipe_version_parsed.bump_minor().bump_prerelease())
        elif command.recipeVersionReleaseType.value == RecipeVersionReleaseType.Patch:
            new_recipe_version_name = str(latest_recipe_version_parsed.bump_patch().bump_prerelease())

    return new_recipe_version_name


def _update_existing_component(
    recipe_components_versions: List[ComponentVersionEntry],
    existing_index: int,
    component_version_id: str,
    component_version_query_service: component_version_query_service.ComponentVersionQueryService,
) -> List[ComponentVersionEntry]:
    existing_entry = recipe_components_versions[existing_index]
    component_version_entity = component_version_query_service.get_component_version(
        component_id=existing_entry.componentId, version_id=component_version_id
    )
    if not component_version_entity:
        raise domain_exception.DomainException(
            f"Component version {component_version_id} for {existing_entry.componentId} not found"
        )
    updated_entry = ComponentVersionEntry(
        componentId=existing_entry.componentId,
        componentVersionId=component_version_id,
        order=existing_entry.order,
        componentName=existing_entry.componentName,
        componentVersionName=component_version_entity.componentVersionName,
        componentVersionType=existing_entry.componentVersionType,
    )
    recipe_components_versions[existing_index] = updated_entry
    return recipe_components_versions


def _add_new_component(
    recipe_components_versions: List[ComponentVersionEntry],
    component_id: str,
    component_version_id: str,
    component_query_service: component_query_service.ComponentQueryService,
    component_version_query_service: component_version_query_service.ComponentVersionQueryService,
) -> List[ComponentVersionEntry]:
    max_order = len(recipe_components_versions)

    component = component_query_service.get_component(component_id=component_id)
    component_version = component_version_query_service.get_component_version(
        component_id=component_id, version_id=component_version_id
    )

    if not component or not component_version:
        raise domain_exception.DomainException(f"Component {component_id} or version {component_version_id} not found")

    new_component_entry = ComponentVersionEntry(
        componentId=component_id,
        componentVersionId=component_version_id,
        order=max_order + 1,
        componentName=component.componentName,
        componentVersionName=component_version.componentVersionName,
        componentVersionType="MAIN",
    )

    recipe_components_versions.append(new_component_entry)
    return recipe_components_versions


def _update_recipe_components(
    recipe_components_versions: List[ComponentVersionEntry],
    command: create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand,
    component_query_service: component_query_service.ComponentQueryService,
    component_version_query_service: component_version_query_service.ComponentVersionQueryService,
) -> List[ComponentVersionEntry]:
    existing_index = next(
        (i for i, entry in enumerate(recipe_components_versions) if entry.componentId == command.componentId.value),
        -1,
    )

    if existing_index >= 0:
        return _update_existing_component(
            recipe_components_versions,
            existing_index,
            command.componentVersionId.value,
            component_version_query_service,
        )
    else:
        return _add_new_component(
            recipe_components_versions,
            command.componentId.value,
            command.componentVersionId.value,
            component_query_service,
            component_version_query_service,
        )


def _create_recipe_version_entity(
    command: create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand,
    last_released_version: recipe_version.RecipeVersion,
    new_recipe_version_name: str,
    recipe_components_versions: List[ComponentVersionEntry],
) -> recipe_version.RecipeVersion:
    current_time = datetime.now(timezone.utc).isoformat()
    return recipe_version.RecipeVersion(
        recipeId=command.recipeId.value,
        recipeVersionName=recipe_version_name_value_object.from_str(new_recipe_version_name).value,
        parentImageUpstreamId=last_released_version.parentImageUpstreamId,
        recipeComponentsVersions=recipe_components_versions,
        recipeName=last_released_version.recipeName,
        recipeVersionDescription=f"Automated build product for component {command.componentId.value} version {command.componentVersionId.value}",
        recipeVersionVolumeSize=last_released_version.recipeVersionVolumeSize,
        recipeVersionIntegrations=last_released_version.recipeVersionIntegrations,
        status=recipe_version.RecipeVersionStatus.Creating,
        createDate=current_time,
        lastUpdateDate=current_time,
        createdBy=command.createdBy.value,
        lastUpdatedBy=command.createdBy.value,
    )


def _publish_recipe_version_creation_event(
    message_bus: message_bus.MessageBus,
    command: create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand,
    recipe_version_entity: recipe_version.RecipeVersion,
    last_released_version: recipe_version.RecipeVersion,
    new_recipe_version_name: str,
) -> None:
    message_bus.publish(
        recipe_version_creation_started.RecipeVersionCreationStarted(
            project_id=command.projectId.value,
            recipe_id=command.recipeId.value,
            recipe_version_id=recipe_version_entity.recipeVersionId,
            parent_image_upstream_id=last_released_version.parentImageUpstreamId,
            recipe_component_versions=recipe_version_entity.recipeComponentsVersions,
            recipe_version_name=new_recipe_version_name,
            recipe_version_volume_size=last_released_version.recipeVersionVolumeSize,
        )
    )


def handle(
    command: create_automated_recipe_version_command.CreateAutomatedRecipeVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService,
    recipe_query_service: recipe_query_service.RecipeQueryService,
    component_query_service: component_query_service.ComponentQueryService,
    component_version_query_service: component_version_query_service.ComponentVersionQueryService,
    mandatory_components_list_query_service: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
) -> str:
    recipe_entity = recipe_query_service.get_recipe(
        project_id=command.projectId.value,
        recipe_id=command.recipeId.value,
    )

    if recipe_entity is None:
        raise domain_exception.DomainException(f"Recipe {command.recipeId.value} not found")

    recipe_versions = recipe_version_query_service.get_recipe_versions(recipe_id=command.recipeId.value)
    last_released_version = _find_last_released_version(recipe_versions, command.recipeId.value)

    latest_recipe_version_name = recipe_version_query_service.get_latest_recipe_version_name(command.recipeId.value)
    new_recipe_version_name = __calculate_new_version_name(command, latest_recipe_version_name)

    (
        mandatory_component_versions,
        prepended_mandatory_components,
        appended_mandatory_components,
    ) = __process_mandatory_components(mandatory_components_list_query_service, recipe_entity)

    mandatory_component_ids = {mc.componentId for mc in mandatory_component_versions}
    user_components = [
        comp
        for comp in last_released_version.recipeComponentsVersions
        if comp.componentId not in mandatory_component_ids
    ]

    user_components = _update_recipe_components(
        user_components,
        command,
        component_query_service,
        component_version_query_service,
    )

    recipe_component_versions = []
    __extend_component_versions_list(recipe_component_versions, prepended_mandatory_components)
    __extend_component_versions_list(recipe_component_versions, user_components)
    __extend_component_versions_list(recipe_component_versions, appended_mandatory_components)

    __validate_component_duplication(
        recipe_component_versions,
        mandatory_component_versions,
    )

    recipe_version_entity = _create_recipe_version_entity(
        command,
        last_released_version,
        new_recipe_version_name,
        recipe_component_versions,
    )

    with uow:
        uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).add(
            recipe_version_entity
        )
        uow.commit()

    _publish_recipe_version_creation_event(
        message_bus,
        command,
        recipe_version_entity,
        last_released_version,
        new_recipe_version_name,
    )

    return recipe_version_entity.recipeVersionId
