from app.packaging.domain.commands.component import share_component_command
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import component_project_association
from app.packaging.domain.ports import component_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def handle(
    command: share_component_command.ShareComponentCommand,
    component_qry_srv: component_query_service.ComponentQueryService,
    uow: unit_of_work.UnitOfWork,
):
    acceptable_roles_for_sharing_component = [
        VirtualWorkbenchRoles.Admin,
        VirtualWorkbenchRoles.ProgramOwner,
    ]

    if not any([item.value in acceptable_roles_for_sharing_component for item in command.userRoles]):
        raise DomainException(
            f"User role is not allowed to share component {command.componentId.value} with project"
            f"{'s' if len(command.projectIds) > 1 else ''} {sorted([item.value for item in command.projectIds])}."
        )
    component_entity = component_qry_srv.get_component(command.componentId.value)
    if component_entity is None:
        raise DomainException(f"Component {command.componentId.value} does not exist.")
    for destination_project_id in command.projectIds:
        component_project_association_entity = component_project_association.ComponentProjectAssociation(
            componentId=component_entity.componentId,
            projectId=destination_project_id.value,
        )
        with uow:
            uow.get_repository(
                repo_key=component_project_association.ComponentProjectAssociationPrimaryKey,
                repo_type=component_project_association.ComponentProjectAssociation,
            ).add(component_project_association_entity)
            uow.commit()
