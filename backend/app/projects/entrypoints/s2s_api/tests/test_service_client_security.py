from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from aws_lambda_powertools.event_handler import api_gateway

from app.projects.domain.model.service_client_assignment import ServiceClientAssignment, ServiceClientAssignmentStatus
from app.projects.domain.ports.projects_query_service import ProjectsQueryService
from app.projects.entrypoints.s2s_api.routers import service_clients
from app.shared.middleware import authorization


@pytest.fixture
def assignment_api():
    query = Mock(spec=ProjectsQueryService)
    command_bus = Mock()
    app = api_gateway.APIGatewayRestResolver(enable_validation=True)
    app.use(middlewares=[authorization.require_auth_context])
    app.include_router(service_clients.init(SimpleNamespace(projects_query_service=query, command_bus=command_bus)))
    return app, query, command_bus


def caller_assignment(status):
    if status is None:
        return None
    return ServiceClientAssignment(
        clientId="fake_client_id",
        projectId="proj-1",
        status=status,
        grantedBy="admin-client",
        createDate="2026-09-16T10:00:00+00:00",
        lastUpdateDate="2026-09-16T10:00:00+00:00",
    )


@pytest.mark.parametrize(
    "caller_status", [None, ServiceClientAssignmentStatus.ACTIVE, ServiceClientAssignmentStatus.REVOKED]
)
@pytest.mark.parametrize("bootstrap", [False, True])
def test_self_assignment_is_denied_before_any_query_or_command(
    assignment_api, authenticated_event, lambda_context, caller_status, bootstrap
):
    app, query, command_bus = assignment_api
    query.get_service_client_assignment.return_value = caller_assignment(caller_status)
    query.get_project_by_id.return_value = object()
    query.list_service_client_assignments.return_value = []
    event = authenticated_event(None, "/projects/proj-1/clients/fake_client_id", "PUT")
    event["requestContext"]["authorizer"]["claims"]["scope"] = "clients/projects/client_assignment.write" + (
        " clients/projects/client_assignment.bootstrap" if bootstrap else ""
    )

    response = app.resolve(event, lambda_context)

    assert response["statusCode"] == 403
    query.get_service_client_assignment.assert_not_called()
    query.list_service_client_assignments.assert_not_called()
    command_bus.handle.assert_not_called()


@pytest.mark.parametrize("bootstrap", [False, True])
def test_management_or_bootstrap_client_can_assign_a_different_client(
    assignment_api, authenticated_event, lambda_context, bootstrap
):
    app, query, command_bus = assignment_api
    query.get_service_client_assignment.return_value = caller_assignment(
        None if bootstrap else ServiceClientAssignmentStatus.ACTIVE
    )
    query.get_project_by_id.return_value = object()
    query.list_service_client_assignments.return_value = []
    event = authenticated_event(None, "/projects/proj-1/clients/packaging-client", "PUT")
    event["requestContext"]["authorizer"]["claims"]["scope"] = "clients/projects/client_assignment.write" + (
        " clients/projects/client_assignment.bootstrap" if bootstrap else ""
    )

    response = app.resolve(event, lambda_context)

    assert response["statusCode"] == 200
    command = command_bus.handle.call_args.args[0]
    assert command.client_id == "packaging-client"
    assert command.granted_by == "fake_client_id"


def test_packaging_scopes_do_not_allow_assignment_management(assignment_api, authenticated_event, lambda_context):
    app, query, command_bus = assignment_api
    query.get_service_client_assignment.return_value = caller_assignment(ServiceClientAssignmentStatus.ACTIVE)
    event = authenticated_event(None, "/projects/proj-1/clients/other-client", "PUT")
    event["requestContext"]["authorizer"]["claims"][
        "scope"
    ] = "clients/packaging/component.write clients/packaging/component.release"

    response = app.resolve(event, lambda_context)

    assert response["statusCode"] == 403
    command_bus.handle.assert_not_called()
