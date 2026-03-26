from app.projects.domain.commands.technologies import update_technology_command as command
from app.projects.domain.events.technologies import technology_updated
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import technology
from app.projects.domain.ports import projects_query_service, technologies_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_update_technology_command(
    cmd: command.UpdateTechnologyCommand,
    uow: unit_of_work.UnitOfWork,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
    technologies_qry_srv: technologies_query_service.TechnologiesQueryService,
    msg_bus: message_bus.MessageBus,
):
    project = projects_qry_srv.get_project_by_id(cmd.project_id.value)
    if not project:
        raise domain_exception.DomainException(
            f"Failed to load project. Project for given ID {cmd.project_id.value} does not exist."
        )

    expected_techs = technologies_qry_srv.list_technologies(project_id=cmd.project_id.value, page_size=0)

    existing_technology = next((t for t in expected_techs if t.id == cmd.id.value), None)
    if not existing_technology:
        raise domain_exception.DomainException(
            f"Failed to update technology. Technology for given ID {cmd.id.value} does not exist."
        )

    existing_technology.name = cmd.name
    existing_technology.description = cmd.description

    with uow:
        uow.get_repository(technology.TechnologyPrimaryKey, technology.Technology).update_entity(
            pk=technology.TechnologyPrimaryKey(id=cmd.id.value, project_id=cmd.project_id.value),
            entity=existing_technology,
        )
        uow.commit()

    msg_bus.publish(
        technology_updated.TechnologyUpdated(
            projectId=cmd.project_id.value, technologyId=cmd.id.value, technologyName=cmd.name
        )
    )
