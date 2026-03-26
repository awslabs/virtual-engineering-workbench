from itertools import batched

from app.projects.domain.commands.users import reassign_user_command as command
from app.projects.domain.events.users import user_reassigned
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_assignment
from app.projects.domain.ports import projects_query_service
from app.projects.domain.value_objects import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work

PROGRAM_OWNER_ALLOWED_ROLES = {
    project_assignment.Role.PROGRAM_OWNER,
    project_assignment.Role.POWER_USER,
    project_assignment.Role.BETA_USER,
    project_assignment.Role.PLATFORM_USER,
    project_assignment.Role.PRODUCT_CONTRIBUTOR,
}

PROGRAM_ADMIN_ALLOWED_ROLES = {
    project_assignment.Role.ADMIN,
    *PROGRAM_OWNER_ALLOWED_ROLES,
}

BATCH_SIZE = 25


def handle_reassign_user_command(  # noqa: C901
    cmd: command.ReAssignUserCommand,
    unit_of_work: unit_of_work.UnitOfWork,
    projects_query_service: projects_query_service.ProjectsQueryService,
    message_bus: message_bus.MessageBus,
):
    project = projects_query_service.get_project_by_id(cmd.project_id.value)
    if not project:
        raise domain_exception.DomainException(
            f"Failed to load program. Program for given ID {cmd.project_id.value} does not exist."
        )

    initiating_user_role_permissions = __get_user_role_boundary(
        project_id=cmd.project_id,
        initiating_user_id=cmd.initiating_user_id,
        projects_query_service=projects_query_service,
    )

    missing_user_assignment = []
    with unit_of_work:
        for user_id_batch in batched(cmd.user_ids, BATCH_SIZE):
            for user_id in user_id_batch:
                user_id = user_id.value.upper()

                user_assignment = projects_query_service.get_user_assignment(cmd.project_id.value, user_id)
                if user_assignment:

                    new_user_roles = {role.value for role in cmd.roles} & initiating_user_role_permissions
                    existing_user_roles = {role for role in user_assignment.roles} - initiating_user_role_permissions
                    user_assignment.roles = [*new_user_roles, *existing_user_roles]

                    unit_of_work.get_repository(
                        project_assignment.AssignmentPrimaryKey, project_assignment.Assignment
                    ).update_entity(
                        pk=project_assignment.AssignmentPrimaryKey(userId=user_id, projectId=cmd.project_id.value),
                        entity=user_assignment,
                    )

                    message_bus.publish(
                        user_reassigned.UserReAssigned(
                            userId=user_id, projectId=cmd.project_id.value, roles=user_assignment.roles
                        )
                    )
                else:
                    missing_user_assignment.append(user_id)

            unit_of_work.commit()

    if missing_user_assignment:
        missing_user_assignment_error = ", ".join(missing_user_assignment)
        raise domain_exception.DomainException(
            f"Users with IDs: {missing_user_assignment_error} are not assigned to program {cmd.project_id.value}"
        )


def __get_user_role_boundary(
    project_id: project_id_value_object.ProjectIdValueObject,
    initiating_user_id: user_id_value_object.UserIdValueObject,
    projects_query_service: projects_query_service.ProjectsQueryService,
):
    if initiating_user_id.type == user_id_value_object.UserIdType.Service:
        return PROGRAM_ADMIN_ALLOWED_ROLES

    initiating_user_assignment = projects_query_service.get_user_assignment(
        project_id.value, initiating_user_id.value.upper()
    )
    if not initiating_user_assignment:
        raise domain_exception.DomainException(
            f"Initiating user {initiating_user_id.value} is not assigned to the program."
        )

    if next((role for role in initiating_user_assignment.roles if role == project_assignment.Role.ADMIN), None):
        return PROGRAM_ADMIN_ALLOWED_ROLES
    elif next(
        (role for role in initiating_user_assignment.roles if role == project_assignment.Role.PROGRAM_OWNER), None
    ):
        return PROGRAM_OWNER_ALLOWED_ROLES
