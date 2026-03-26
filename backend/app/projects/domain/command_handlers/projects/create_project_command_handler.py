from datetime import datetime, timezone

from app.projects.domain.commands.projects import create_project_command
from app.projects.domain.events.projects import project_created
from app.projects.domain.model import project
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_create_project_command(
    cmd: create_project_command.CreateProjectCommand,
    uow: unit_of_work.UnitOfWork,
    msg_bus: message_bus.MessageBus,
) -> str:
    current_time = datetime.now(timezone.utc).isoformat()
    proj = project.Project(
        projectName=cmd.name,
        projectDescription=cmd.description,
        isActive=cmd.isActive,
        createDate=current_time,
        lastUpdateDate=current_time,
    )

    with uow:
        uow.get_repository(project.ProjectPrimaryKey, project.Project).add(proj)
        uow.commit()

    msg_bus.publish(
        project_created.ProjectCreated(
            projectId=proj.projectId,
            projectName=proj.projectName,
            projectDescription=proj.projectDescription,
            isActive=proj.isActive,
        )
    )

    return proj.projectId
