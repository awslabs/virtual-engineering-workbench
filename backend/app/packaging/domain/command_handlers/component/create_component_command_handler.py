from datetime import datetime, timezone

from app.packaging.domain.commands.component import create_component_command
from app.packaging.domain.model.component import component, component_project_association
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: create_component_command.CreateComponentCommand,
    uow: unit_of_work.UnitOfWork,
):
    current_time = datetime.now(timezone.utc).isoformat()
    component_entity = component.Component(
        componentId=command.componentId.value,
        componentDescription=command.componentDescription.value,
        componentName=command.componentName.value,
        componentPlatform=command.componentSystemConfiguration.platform,
        componentSupportedArchitectures=command.componentSystemConfiguration.supported_architectures,
        componentSupportedOsVersions=command.componentSystemConfiguration.supported_os_versions,
        status=component.ComponentStatus.Created,
        createDate=current_time,
        lastUpdateDate=current_time,
        createdBy=command.createdBy.value,
        lastUpdatedBy=command.createdBy.value,
    )
    component_project_association_entity = component_project_association.ComponentProjectAssociation(
        componentId=component_entity.componentId,
        projectId=command.projectId.value,
    )

    with uow:
        uow.get_repository(repo_key=component.ComponentPrimaryKey, repo_type=component.Component).add(component_entity)
        uow.get_repository(
            repo_key=component_project_association.ComponentProjectAssociationPrimaryKey,
            repo_type=component_project_association.ComponentProjectAssociation,
        ).add(component_project_association_entity)
        uow.commit()
