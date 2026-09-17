from datetime import datetime, timezone

from app.projects.domain.commands.service_clients import revoke_service_client_assignment_command
from app.projects.domain.model import service_client_assignment
from app.projects.domain.ports import projects_query_service as projects_query_service_port
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_revoke_service_client_assignment_command(
    cmd: revoke_service_client_assignment_command.RevokeServiceClientAssignmentCommand,
    uow: unit_of_work.UnitOfWork,
    projects_query_service: projects_query_service_port.ProjectsQueryService,
) -> None:
    existing = projects_query_service.get_service_client_assignment(cmd.project_id.value, cmd.client_id)
    if existing is None or existing.status == service_client_assignment.ServiceClientAssignmentStatus.REVOKED:
        return

    existing.status = service_client_assignment.ServiceClientAssignmentStatus.REVOKED
    existing.lastUpdateDate = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(
            service_client_assignment.ServiceClientAssignmentPrimaryKey,
            service_client_assignment.ServiceClientAssignment,
        ).update_entity(
            service_client_assignment.ServiceClientAssignmentPrimaryKey(
                clientId=cmd.client_id,
                projectId=cmd.project_id.value,
            ),
            existing,
        )
        uow.commit()
