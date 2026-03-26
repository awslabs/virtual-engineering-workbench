from datetime import datetime, timezone

from app.packaging.domain.commands.component import (
    update_mandatory_components_list_command,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import (
    component_version,
    mandatory_components_list,
)
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.ports import (
    component_version_query_service,
    mandatory_components_list_query_service,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __validate_component_lists(prepended_components, appended_components):
    if not prepended_components and not appended_components:
        raise domain_exception.DomainException(
            "At least one component must be specified as either prepended or appended."
        )

    prepended_ids = {comp.componentId for comp in prepended_components}
    appended_ids = {comp.componentId for comp in appended_components}
    duplicate_ids = prepended_ids & appended_ids

    if duplicate_ids:
        raise domain_exception.DomainException(
            f"Components cannot be both prepended and appended: {sorted(duplicate_ids)}."
        )


def __validate_component_versions(
    components,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
):
    for comp in components:
        component_version_entity = component_version_qry_srv.get_component_version(
            component_id=comp.componentId,
            version_id=comp.componentVersionId,
        )

        if component_version_entity is None:
            raise domain_exception.DomainException(
                f"Version {comp.componentVersionId} of component {comp.componentId} does not exist."
            )
        if component_version_entity.status != component_version.ComponentVersionStatus.Released:
            raise domain_exception.DomainException(
                f"Version {comp.componentVersionId} of component {comp.componentId} has not been released."
            )


def __create_positioned_components(prepended_components, appended_components):
    positioned_components = []

    for order, comp in enumerate(prepended_components, start=1):
        positioned_comp = component_version_entry.ComponentVersionEntry(
            componentId=comp.componentId,
            componentName=comp.componentName,
            componentVersionId=comp.componentVersionId,
            componentVersionName=comp.componentVersionName,
            componentVersionType=comp.componentVersionType,
            order=order,
            position=component_version_entry.ComponentVersionEntryPosition.Prepend,
        )
        positioned_components.append(positioned_comp)

    for order, comp in enumerate(appended_components, start=1):
        positioned_comp = component_version_entry.ComponentVersionEntry(
            componentId=comp.componentId,
            componentName=comp.componentName,
            componentVersionId=comp.componentVersionId,
            componentVersionName=comp.componentVersionName,
            componentVersionType=comp.componentVersionType,
            order=order,
            position=component_version_entry.ComponentVersionEntryPosition.Append,
        )
        positioned_components.append(positioned_comp)

    return positioned_components


def handle(
    command: update_mandatory_components_list_command.UpdateMandatoryComponentsListCommand,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    mandatory_components_list_qry_srv: mandatory_components_list_query_service.MandatoryComponentsListQueryService,
    uow: unit_of_work.UnitOfWork,
):
    prepended_components = command.prependedComponentsVersions.value
    appended_components = command.appendedComponentsVersions.value

    __validate_component_lists(prepended_components, appended_components)

    all_components = list(prepended_components) + list(appended_components)
    __validate_component_versions(all_components, component_version_qry_srv)

    architecture = command.mandatoryComponentsListArchitecture.value
    os = command.mandatoryComponentsListOsVersion.value
    platform = command.mandatoryComponentsListPlatform.value

    mandatory_component_list = mandatory_components_list_qry_srv.get_mandatory_components_list(
        platform=platform, os=os, architecture=architecture
    )

    if mandatory_component_list is None:
        raise domain_exception.DomainException(
            f"Mandatory components list for {platform} {os} ({architecture}) can not be found."
        )

    positioned_components = __create_positioned_components(prepended_components, appended_components)
    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(
            mandatory_components_list.MandatoryComponentsListPrimaryKey,
            mandatory_components_list.MandatoryComponentsList,
        ).update_attributes(
            mandatory_components_list.MandatoryComponentsListPrimaryKey(
                mandatoryComponentsListPlatform=platform,
                mandatoryComponentsListOsVersion=os,
                mandatoryComponentsListArchitecture=architecture,
            ),
            mandatoryComponentsVersions=[comp.dict() for comp in positioned_components],
            lastUpdateDate=current_time,
            lastUpdatedBy=command.lastUpdatedBy.value,
        )
        uow.commit()
