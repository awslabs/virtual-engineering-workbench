from datetime import datetime, timezone

from app.projects.domain.commands.service_clients import put_service_client_assignment_command
from app.projects.domain.model import service_client_assignment
from app.projects.domain.ports import projects_query_service as projects_query_service_port
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_put_service_client_assignment_command(
    cmd: put_service_client_assignment_command.PutServiceClientAssignmentCommand,
    uow: unit_of_work.UnitOfWork,
    projects_query_service: projects_query_service_port.ProjectsQueryService,
) -> None:
    existing = projects_query_service.get_service_client_assignment(cmd.project_id.value, cmd.client_id)
    if existing and existing.status == service_client_assignment.ServiceClientAssignmentStatus.ACTIVE:
        return

    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        repository = uow.get_repository(
            service_client_assignment.ServiceClientAssignmentPrimaryKey,
            service_client_assignment.ServiceClientAssignment,
        )
        if existing is None:
            repository.add(
                service_client_assignment.ServiceClientAssignment(
                    clientId=cmd.client_id,
                    projectId=cmd.project_id.value,
                    status=service_client_assignment.ServiceClientAssignmentStatus.ACTIVE,
                    grantedBy=cmd.granted_by,
                    createDate=current_time,
                    lastUpdateDate=current_time,
                )
            )
        else:
            existing.status = service_client_assignment.ServiceClientAssignmentStatus.ACTIVE
            existing.grantedBy = cmd.granted_by
            existing.lastUpdateDate = current_time
            repository.update_entity(
                service_client_assignment.ServiceClientAssignmentPrimaryKey(
                    clientId=cmd.client_id,
                    projectId=cmd.project_id.value,
                ),
                existing,
            )
        uow.commit()
