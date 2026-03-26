from app.projects.domain.commands.users import assign_user_command as command
from app.projects.domain.events.users import user_assigned
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_assignment, user
from app.projects.domain.ports import projects_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle_assign_user_command(
    cmd: command.AssignUserCommand,
    unit_of_work: unit_of_work.UnitOfWork,
    projects_query_service: projects_query_service.ProjectsQueryService,
    message_bus: message_bus.MessageBus,
):
    project = projects_query_service.get_project_by_id(cmd.project_id.value)
    if not project:
        raise domain_exception.DomainException(
            f"Failed to load project. Project for given ID {cmd.project_id.value} does not exist."
        )

    to_be_assigned_user_id = cmd.user_id.value.upper()

    to_be_assigned_user_assignment = projects_query_service.get_user_assignment(
        project_id=cmd.project_id.value, user_id=to_be_assigned_user_id
    )
    if to_be_assigned_user_assignment:
        raise domain_exception.DomainException(f"User with User ID {to_be_assigned_user_id} already exists.")

    assigned_roles = [role.value for role in cmd.roles]

    assignment = project_assignment.Assignment(
        userId=to_be_assigned_user_id,
        projectId=cmd.project_id.value,
        roles=assigned_roles,
        activeDirectoryGroups=[],
        activeDirectoryGroupStatus=user.UserADStatus.PENDING,
    )

    with unit_of_work:
        unit_of_work.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).add(
            assignment
        )
        unit_of_work.commit()

    message_bus.publish(
        user_assigned.UserAssigned(userId=assignment.userId, projectId=assignment.projectId, roles=assignment.roles)
    )
