from http import HTTPStatus

from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler import api_gateway, content_types
from aws_lambda_powertools.event_handler.api_gateway import Router

from app.projects.domain.commands.users import assign_user_command, reassign_user_command, unassign_user_command
from app.projects.domain.value_objects import (
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.projects.entrypoints.s2s_api import bootstrapper
from app.projects.entrypoints.s2s_api.model import api_model

tracer = Tracer()


def init(dependencies: bootstrapper.Dependencies) -> Router:
    router = Router()

    @tracer.capture_method
    @router.get("/projects/<project_id>/users")
    def get_project_users(
        project_id: str,
    ) -> api_gateway.Response[api_model.GetProjectAssignmentsResponse]:
        """Returns a list of project assignments with paging."""

        assignments = dependencies.projects_query_service.list_users_by_project(
            project_id=project_id,
        )

        return api_gateway.Response(
            status_code=HTTPStatus.OK,
            body=api_model.GetProjectAssignmentsResponse(
                assignments=[api_model.GetProjectAssignmentsResponseItem.parse_obj(a.dict()) for a in assignments],
            ),
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.post("/projects/<project_id>/users")
    def assign_project_user(
        request: api_model.AssignUserRequest,
        project_id: str,
    ) -> api_gateway.Response[api_model.AssignUserResponse]:
        """Assigns user to a project"""

        dependencies.command_bus.handle(
            assign_user_command.AssignUserCommand(
                project_id=project_id_value_object.from_str(project_id),
                user_id=user_id_value_object.from_str(request.userId.upper()),
                roles=[user_role_value_object.from_str(role) for role in request.roles or []],
            )
        )

        return api_gateway.Response(
            status_code=HTTPStatus.OK,
            body=api_model.AssignUserResponse(),
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.delete("/projects/<project_id>/users")
    def remove_project_users(
        request: api_model.RemoveUsersRequest, project_id: str
    ) -> api_gateway.Response[api_model.RemoveUsersResponse]:
        """Removes multiple users from a project/program"""

        user_ids = [user_id_value_object.from_str(user_id.upper()) for user_id in request.userIds]

        cmd = unassign_user_command.UnAssignUserCommand(
            project_id=project_id_value_object.from_str(project_id),
            user_ids=user_ids,
        )
        dependencies.command_bus.handle(cmd)

        return api_gateway.Response(
            status_code=HTTPStatus.OK,
            body=api_model.RemoveUsersResponse(),
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.put("/projects/<project_id>/users")
    def reassign_project_user(
        request: api_model.ReAssignUsersRequest,
        project_id: str,
    ) -> api_gateway.Response[api_model.ReAssignUsersResponse]:
        """Reassigns users to a project"""

        user_principal_name = router.context.get("user_principal").user_name.upper()

        dependencies.command_bus.handle(
            reassign_user_command.ReAssignUserCommand(
                project_id=project_id_value_object.from_str(project_id),
                user_ids=[user_id_value_object.from_str(user_id.upper()) for user_id in request.userIds or []],
                initiating_user_id=user_id_value_object.from_str(
                    user_principal_name, user_id_value_object.UserIdType.Service
                ),
                roles=[user_role_value_object.from_str(role) for role in request.roles or []],
            )
        )

        return api_gateway.Response(
            status_code=HTTPStatus.OK,
            body=api_model.ReAssignUsersResponse(),
            content_type=content_types.APPLICATION_JSON,
        )

    @tracer.capture_method
    @router.get("/projects/<project_id>/users/<user_id>")
    def get_user_roles(
        project_id: str,
        user_id: str,
    ) -> api_gateway.Response[api_model.GetUserRolesResponse]:
        """Returns a list of roles assigned to a user for a project."""

        project_assignment = dependencies.projects_query_service.get_user_assignment(
            project_id=project_id,
            user_id=user_id.upper(),
        )

        return api_gateway.Response(
            status_code=HTTPStatus.OK,
            body=api_model.GetUserRolesResponse(roles=project_assignment.roles if project_assignment else []),
            content_type=content_types.APPLICATION_JSON,
        )

    return router
