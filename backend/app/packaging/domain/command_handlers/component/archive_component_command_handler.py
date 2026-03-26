from datetime import datetime, timezone

from app.packaging.domain.commands.component import archive_component_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component, component_version
from app.packaging.domain.ports import component_query_service, component_version_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: archive_component_command.ArchiveComponentCommand,
    component_qry_srv: component_query_service.ComponentQueryService,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    uow: unit_of_work.UnitOfWork,
):
    component_entity = component_qry_srv.get_component(command.componentId.value)

    if component_entity is None:
        raise domain_exception.DomainException(f"Component {command.componentId.value} can not be found.")

    components_versions_entities = component_version_qry_srv.get_component_versions(
        component_id=command.componentId.value
    )

    for component_version_entity in components_versions_entities:
        if component_version_entity.status is not component_version.ComponentVersionStatus.Retired:
            raise domain_exception.DomainException(
                f"Component {command.componentId.value} cannot be retired because component version "
                f"{component_version_entity.componentVersionId} is in {component_version_entity.status} status."
            )

    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(component.ComponentPrimaryKey, component.Component).update_attributes(
            component.ComponentPrimaryKey(
                componentId=command.componentId.value,
            ),
            lastUpdateBy=command.lastUpdatedBy.value,
            lastUpdateDate=current_time,
            status=component.ComponentStatus.Archived,
        )
        uow.commit()
