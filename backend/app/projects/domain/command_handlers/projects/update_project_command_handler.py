from datetime import datetime, timezone

from app.projects.domain.commands.projects import update_project_command
from app.projects.domain.events.projects import project_updated
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_update_project_command(
    cmd: update_project_command.UpdateProjectCommand,
    uow: unit_of_work.UnitOfWork,
    msg_bus: message_bus.MessageBus,
) -> None:

    current_time = datetime.now(timezone.utc).isoformat()
    project_id = project.ProjectPrimaryKey(projectId=cmd.id.value)

    with uow:
        proj = uow.get_repository(project.ProjectPrimaryKey, project.Project).get(project_id)

        if not proj:
            raise domain_exception.DomainException(f"Project {cmd.id.value} does not exist")

        proj.projectName = cmd.name
        proj.projectDescription = cmd.description
        proj.isActive = cmd.isActive
        proj.lastUpdateDate = current_time

        uow.get_repository(project.ProjectPrimaryKey, project.Project).update_entity(
            pk=project_id,
            entity=proj,
        )
        uow.commit()

    msg_bus.publish(
        project_updated.ProjectUpdated(
            projectId=cmd.id.value,
            projectName=cmd.name,
            projectDescription=cmd.description,
            isActive=cmd.isActive,
        )
    )
