from http import HTTPStatus

from aws_lambda_powertools import Tracer
from aws_lambda_powertools.event_handler import api_gateway, content_types
from aws_lambda_powertools.event_handler.api_gateway import Router
from aws_lambda_powertools.event_handler.exceptions import NotFoundError

from app.projects.domain.commands.service_clients import (
    put_service_client_assignment_command,
    revoke_service_client_assignment_command,
)
from app.projects.domain.value_objects import project_id_value_object
from app.projects.entrypoints.s2s_api import bootstrapper
from app.projects.entrypoints.s2s_api.model import api_model

tracer = Tracer()


def _response(client_id: str, project_id: str, status: api_model.Status):
    return api_gateway.Response(
        status_code=HTTPStatus.OK,
        body=api_model.GetServiceClientAssignmentResponse(
            assignment=api_model.ServiceClientAssignment(
                clientId=client_id,
                projectId=project_id,
                status=status,
            )
        ),
        content_type=content_types.APPLICATION_JSON,
    )


def init(dependencies: bootstrapper.Dependencies) -> Router:
    router = Router()

    @tracer.capture_method
    @router.put("/projects/<project_id>/clients/<client_id>")
    def put_service_client_assignment(project_id: str, client_id: str):
        granted_by = router.context["user_principal"].user_name
        dependencies.command_bus.handle(
            put_service_client_assignment_command.PutServiceClientAssignmentCommand(
                project_id=project_id_value_object.from_str(project_id),
                client_id=client_id,
                granted_by=granted_by,
            )
        )
        return _response(client_id, project_id, api_model.Status.ACTIVE)

    @tracer.capture_method
    @router.get("/projects/<project_id>/clients/<client_id>")
    def get_service_client_assignment(project_id: str, client_id: str):
        assignment = dependencies.projects_query_service.get_service_client_assignment(project_id, client_id)
        if assignment is None:
            raise NotFoundError("Service client assignment not found")
        return _response(client_id, project_id, api_model.Status(assignment.status.value))

    @tracer.capture_method
    @router.delete("/projects/<project_id>/clients/<client_id>")
    def revoke_service_client_assignment(project_id: str, client_id: str):
        revoked_by = router.context["user_principal"].user_name
        dependencies.command_bus.handle(
            revoke_service_client_assignment_command.RevokeServiceClientAssignmentCommand(
                project_id=project_id_value_object.from_str(project_id),
                client_id=client_id,
                revoked_by=revoked_by,
            )
        )
        return _response(client_id, project_id, api_model.Status.REVOKED)

    return router
