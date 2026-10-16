from datetime import datetime, timezone

import semver

from app.packaging.domain.commands.component import retire_component_version_command
from app.packaging.domain.events.component import component_version_retirement_started
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import component_version, mandatory_components_list
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import (
    component_version_query_service,
    mandatory_components_list_query_service,
    recipe_version_query_service,
)
from app.shared.adapters.message_bus.message_bus import MessageBus
from app.shared.adapters.unit_of_work_v2.unit_of_work import UnitOfWork
from app.shared.middleware.authorization import VirtualWorkbenchRoles


# An association can outlive its version: retirement removes it asynchronously, and before the
# association writes were conditional, parallel retirements lost removals. A retired (or deleted)
# version no longer depends on anything, so its stale entry must not block a retirement.
def __is_retired_component_version(
    entry,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService | None,
) -> bool:
    if component_version_qry_srv is None:
        return False
    associated = component_version_qry_srv.get_component_version(
        component_id=entry.componentId, version_id=entry.componentVersionId
    )
    return associated is None or associated.status == component_version.ComponentVersionStatus.Retired


def __is_retired_recipe_version(
    entry,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService | None,
) -> bool:
    if recipe_version_qry_srv is None:
        return False
    associated = recipe_version_qry_srv.get_recipe_version(recipe_id=entry.recipeId, version_id=entry.recipeVersionId)
    return associated is None or associated.status == recipe_version.RecipeVersionStatus.Retired


def __validate_associated_components_versions_list(
    component_version_entity: component_version.ComponentVersion,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService | None = None,
):
    rc_count = 0
    associated_components_versions_list = [
        entry
        for entry in component_version_entity.associatedComponentsVersions or []
        if not __is_retired_component_version(entry, component_version_qry_srv)
    ]
    for component_version_entry in associated_components_versions_list:
        component_version_parsed = semver.Version.parse(component_version_entry.componentVersionName)
        if component_version_parsed.prerelease:
            rc_count += 1

    # Raise if there is at least one released component version in the list
    if len(associated_components_versions_list) > rc_count:
        raise DomainException(
            f"Version {component_version_entity.componentVersionId} of component "
            f"{component_version_entity.componentId} can't be retired if it has associated components versions."
        )


def __validate_associated_mandatory_components_lists(
    component_version_entity: component_version.ComponentVersion,
    mandatory_components_lists: list[mandatory_components_list.MandatoryComponentsList],
):
    for mandatory_component_list in mandatory_components_lists:
        if any(
            [
                mandatory_component_version
                for mandatory_component_version in mandatory_component_list.mandatoryComponentsVersions
                if mandatory_component_version.componentId == component_version_entity.componentId
                and mandatory_component_version.componentVersionId == component_version_entity.componentVersionId
                and mandatory_component_version.componentVersionName == component_version_entity.componentVersionName
            ]
        ):
            raise DomainException(
                f"Version {component_version_entity.componentVersionId} of component "
                f"{component_version_entity.componentId} can't be retired if it is included in a mandatory components list."
            )


def __validate_associated_recipes_versions_list(
    component_version_entity: component_version.ComponentVersion,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService | None = None,
):
    rc_count = 0
    associated_recipes_versions_list = [
        entry
        for entry in component_version_entity.associatedRecipesVersions or []
        if not __is_retired_recipe_version(entry, recipe_version_qry_srv)
    ]
    for recipe_version_entry in associated_recipes_versions_list:
        recipe_version_parsed = semver.Version.parse(recipe_version_entry.recipeVersionName)
        if recipe_version_parsed.prerelease:
            rc_count += 1

    # Raise if there is at least one released recipe version in the list
    if len(associated_recipes_versions_list) > rc_count:
        raise DomainException(
            f"Version {component_version_entity.componentVersionId} of component "
            f"{component_version_entity.componentId} can't be retired if it has associated recipes versions."
        )


def handle(
    command: retire_component_version_command.RetireComponentVersionCommand,
    component_version_query_service: component_version_query_service.ComponentVersionQueryService,
    mandatory_components_list_query_service: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
    message_bus: MessageBus,
    uow: UnitOfWork,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService | None = None,
):
    component_version_entity: component_version.ComponentVersion = (
        component_version_query_service.get_component_version(
            component_id=command.componentId.value, version_id=command.componentVersionId.value
        )
    )

    if component_version_entity is None:
        raise DomainException(
            f"Version {command.componentVersionId.value} of component {command.componentId.value} does not exist."
        )

    try:
        component_version_name = component_version_entity.componentVersionName
        component_version_parsed = semver.Version.parse(component_version_name)
    except:
        raise DomainException(f"Version {component_version_name} is not a valid SemVer string.")

    acceptable_states_for_retirement = [
        component_version.ComponentVersionStatus.Failed,
        component_version.ComponentVersionStatus.Released,
        component_version.ComponentVersionStatus.Validated,
    ]
    acceptable_roles_for_released_retirement = [
        VirtualWorkbenchRoles.Admin,
        VirtualWorkbenchRoles.ProgramOwner,
        VirtualWorkbenchRoles.PowerUser,
    ]

    if component_version_entity.status not in acceptable_states_for_retirement:
        raise DomainException(
            f"Version {command.componentVersionId.value} of component {command.componentId.value} "
            f"can't be retired while in {component_version_entity.status} status: "
            f"only {component_version.ComponentVersionStatus.Failed}, "
            f"{component_version.ComponentVersionStatus.Released}, "
            f"and {component_version.ComponentVersionStatus.Validated} states are accepted."
        )
    # Component versions in release candidate are not subject to roles filtering
    if (
        not any([item.value in acceptable_roles_for_released_retirement for item in command.userRoles])
        and component_version_parsed.prerelease is None
    ):
        raise DomainException(
            f"Version {component_version_name} of component {command.componentId.value} can't be retired by "
            f"{sorted([item.value for item in command.userRoles])} role{'s' if len(command.userRoles) > 1 else ''}."
        )

    mandatory_components_lists = mandatory_components_list_query_service.get_mandatory_components_lists()

    __validate_associated_components_versions_list(
        component_version_entity=component_version_entity,
        component_version_qry_srv=component_version_query_service,
    )
    __validate_associated_mandatory_components_lists(
        component_version_entity=component_version_entity, mandatory_components_lists=mandatory_components_lists
    )
    __validate_associated_recipes_versions_list(
        component_version_entity=component_version_entity,
        recipe_version_qry_srv=recipe_version_query_service,
    )

    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(
            component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
        ).update_attributes(
            component_version.ComponentVersionPrimaryKey(
                componentId=command.componentId.value,
                componentVersionId=command.componentVersionId.value,
            ),
            lastUpdateDate=current_time,
            lastUpdateBy=command.lastUpdatedBy.value,
            status=component_version.ComponentVersionStatus.Updating,
        )
        uow.commit()
    message_bus.publish(
        component_version_retirement_started.ComponentVersionRetirementStarted(
            componentId=command.componentId.value,
            componentVersionId=command.componentVersionId.value,
            componentBuildVersionArn=component_version_entity.componentBuildVersionArn,
            componentVersionDependencies=component_version_entity.componentVersionDependencies,
        )
    )
