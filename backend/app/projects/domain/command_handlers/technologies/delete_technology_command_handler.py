from app.projects.domain.commands.technologies import delete_technology_command as command
from app.projects.domain.events.technologies import technology_deleted
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import technology
from app.projects.domain.ports import projects_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_delete_technology_command(
    cmd: command.DeleteTechnologyCommand,
    uow: unit_of_work.UnitOfWork,
    projects_qry_srv: projects_query_service.ProjectsQueryService,
    msg_bus: message_bus.MessageBus,
):
    project_accounts = projects_qry_srv.list_project_accounts(
        project_id=cmd.project_id.value, technology_id=cmd.id.value
    )
    if project_accounts:
        raise domain_exception.DomainException(
            f"Failed to delete technology. Technology for given ID {cmd.id.value} is still associated with AWS accounts."
        )

    with uow:
        uow.get_repository(technology.TechnologyPrimaryKey, technology.Technology).remove(
            technology.TechnologyPrimaryKey(id=cmd.id.value, project_id=cmd.project_id.value)
        )
        uow.commit()

    msg_bus.publish(
        technology_deleted.TechnologyDeleted(
            projectId=cmd.project_id.value,
            technologyId=cmd.id.value,
        )
    )
