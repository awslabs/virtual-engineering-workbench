from datetime import datetime, timezone

from app.projects.domain.commands.technologies import add_technology as command
from app.projects.domain.events.technologies import technology_added
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import technology
from app.projects.domain.ports import projects_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_add_technology_command(
    cmd: command.AddTechnologyCommand,
    uow: unit_of_work.UnitOfWork,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
    msg_bus: message_bus.MessageBus,
):
    project = projects_qry_srv.get_project_by_id(cmd.project_id.value)
    if not project:
        raise domain_exception.DomainException(
            f"Failed to load project. Project for given ID {cmd.project_id.value} does not exist."
        )
    current_time = datetime.now(timezone.utc).isoformat()
    tech = technology.Technology(
        project_id=cmd.project_id.value,
        name=cmd.name,
        description=cmd.description,
        createDate=current_time,
        lastUpdateDate=current_time,
    )

    with uow:
        uow.get_repository(technology.TechnologyPrimaryKey, technology.Technology).add(tech)
        uow.commit()

    msg_bus.publish(
        technology_added.TechnologyAdded(projectId=cmd.project_id.value, technologyId=tech.id, technologyName=cmd.name)
    )
