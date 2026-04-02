import importlib
import json
import logging
import unittest
from unittest.mock import create_autospec, patch

import assertpy

from app.projects.domain.command_handlers.enrolments import (
    approve_enrolments_command_handler,
    enrol_user_to_program_command_handler,
)
from app.projects.domain.commands.enrolments import approve_enrolments_command, enrol_user_to_program_command
from app.projects.domain.model import enrolment, project_assignment
from app.projects.entrypoints.s2s_api import bootstrapper
from app.projects.entrypoints.s2s_api.model import api_model
from app.projects.entrypoints.s2s_api.tests import fake_classes
from app.shared.adapters.message_bus import event_bridge_message_bus, in_memory_command_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work as shared_dynamodb_unit_of_work


def get_mock_dependencies(
    projects_query_service=None,
    enrolment_query_service=None,
) -> bootstrapper.Dependencies:
    command_bus = (
        in_memory_command_bus.InMemoryCommandBus(logger=create_autospec(spec=logging.Logger))
        .register_handler(
            approve_enrolments_command.ApproveEnrolmentsCommand,
            lambda command: approve_enrolments_command_handler.handle_approve_enrolments_command(
                cmd=command,
                uow=unittest.mock.create_autospec(
                    spec=shared_dynamodb_unit_of_work.UnitOfWork,
                ),
                enrolment_qry_srv=enrolment_query_service or fake_classes.FakeEnrolmentsQueryService(),
                project_qry_srv=projects_query_service or fake_classes.FakeProjectsQueryService(),
                message_bus=unittest.mock.create_autospec(
                    spec=event_bridge_message_bus.EventBridgeMessageBus,
                ),
            ),
        )
        .register_handler(
            enrol_user_to_program_command.EnrolUserToProgramCommand,
            lambda command: enrol_user_to_program_command_handler.handle_enrol_user_to_program_command(
                cmd=command,
                uow=unittest.mock.create_autospec(
                    spec=shared_dynamodb_unit_of_work.UnitOfWork,
                ),
                projects_qry_srv=projects_query_service or fake_classes.FakeProjectsQueryService(),
                enrolment_qry_srv=enrolment_query_service or fake_classes.FakeEnrolmentsQueryService(),
                msg_bus=unittest.mock.create_autospec(
                    spec=event_bridge_message_bus.EventBridgeMessageBus,
                ),
            ),
        )
    )

    return bootstrapper.Dependencies(
        technologies_query_service=fake_classes.FakeTechnologiesQueryService(),
        projects_query_service=projects_query_service or fake_classes.FakeProjectsQueryService(),
        enrolment_query_service=enrolment_query_service or fake_classes.FakeEnrolmentsQueryService(),
        command_bus=command_bus,
    )


@patch("app.projects.entrypoints.s2s_api.bootstrapper.bootstrap", return_value=get_mock_dependencies())
def test_get_projects(lambda_context, authenticated_event):
    # Arrange
    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    minimal_event = authenticated_event(None, "/projects", "GET", {"pageSize": "25"})

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projects)).is_equal_to(5)


@patch("app.projects.entrypoints.s2s_api.routers.enrolments.uuid4", return_value="testUUID")
@patch(
    "app.projects.entrypoints.s2s_api.bootstrapper.bootstrap",
    return_value=get_mock_dependencies(
        enrolment_query_service=fake_classes.FakeEnrolmentsQueryService(
            enrolments=[enrolment.Enrolment(id="testUUID", projectId="P0", userId="user_id", status="Pending")]
        )
    ),
)
def test_can_approve_enrolment_for_new_user(mock_deps, mock_uuid, lambda_context, authenticated_event):
    # Arrange
    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    project_id = "P0"
    user_id = "user"
    request = api_model.EnrolUserRequest(
        userId=user_id, userEmail="test@test.de", approverId="testApprover"
    ).model_dump_json()
    minimal_event = authenticated_event(request, f"/projects/{project_id}/enrolments", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


@patch("app.projects.entrypoints.s2s_api.routers.enrolments.uuid4", return_value="testUUID")
@patch(
    "app.projects.entrypoints.s2s_api.bootstrapper.bootstrap",
    return_value=get_mock_dependencies(
        enrolment_query_service=fake_classes.FakeEnrolmentsQueryService(
            enrolments=[
                enrolment.Enrolment(id="testUUID", projectId="P0", userId="userWithPendingEnrolment", status="Pending")
            ]
        )
    ),
)
def test_can_approve_enrolment_for_already_enrolled_but_pending_user(
    mock_deps, mock_uuid, lambda_context, authenticated_event
):
    # Arrange
    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    project_id = "P0"
    user_id = "userWithPendingEnrolment"
    request = api_model.EnrolUserRequest(
        userId=user_id, userEmail="test@test.de", approverId="testApprover"
    ).model_dump_json()
    minimal_event = authenticated_event(request, f"/projects/{project_id}/enrolments", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


@patch("app.projects.adapters.query_services.dynamodb_query_service.DynamoDBProjectsQueryService", autospec=True)
def test_get_project_users_should_return_all_users(projects_qs_mock, lambda_context, authenticated_event):
    # Arrange
    projects_qs_mock.return_value = fake_classes.FakeProjectsQueryService()

    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    minimal_event = authenticated_event(None, "/projects/project-id/users", "GET")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    assertpy.assert_that(json.loads(result["body"])).is_equal_to(
        {
            "assignments": [
                {
                    "userId": "T0000AA",
                    "roles": [project_assignment.Role.PLATFORM_USER.value],
                    "userEmail": None,
                }
            ],
        }
    )


@patch(
    "app.projects.domain.command_handlers.users.assign_user_command_handler.handle_assign_user_command", autospec=True
)
def test_assign_user_should_create_assignment(mock_command_handler, lambda_context, authenticated_event):
    # Arrange
    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    request = api_model.AssignUserRequest(userId="T0000AA", roles=[project_assignment.Role.PLATFORM_USER.value])
    minimal_event = authenticated_event(request.model_dump_json(), "/projects/project-id/users", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handler.assert_called_once()


@patch(
    "app.projects.domain.command_handlers.users.reassign_user_command_handler.handle_reassign_user_command",
    autospec=True,
)
def test_reassign_user_should_update_assignment(mock_command_handler, lambda_context, authenticated_event):
    # Arrange
    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    request = api_model.ReAssignUsersRequest.model_validate({"roles": [project_assignment.Role.PLATFORM_USER.value]})
    minimal_event = authenticated_event(json.dumps(request.model_dump()), "/projects/project-id/users", "PUT")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handler.assert_called_once()


@patch("app.projects.adapters.query_services.dynamodb_query_service.DynamoDBProjectsQueryService", autospec=True)
def test_get_user_roles(projects_qs_mock, lambda_context, authenticated_event):
    # Arrange
    projects_qs_mock.return_value = fake_classes.FakeProjectsQueryService()

    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    minimal_event = authenticated_event(None, "/projects/123/users/U0", "GET")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetUserRolesResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.roles)).is_equal_to(2)
    assertpy.assert_that(json.loads(result["body"])).is_equal_to(
        {
            "roles": [project_assignment.Role.ADMIN.value, project_assignment.Role.PLATFORM_USER.value],
        }
    )


@patch(
    "app.projects.domain.command_handlers.users.unassign_user_command_handler.handle_unassign_user_command",
    autospec=True,
)
def test_offboard_multiple_users_should_remove_assignments(mock_command_handler, lambda_context, authenticated_event):
    # Arrange
    from app.projects.entrypoints.s2s_api import handler

    importlib.reload(handler)

    user_id = "T0000AA"
    request = api_model.RemoveUsersRequest(userIds=[user_id]).model_dump_json()
    minimal_event = authenticated_event(request, "/projects/project-id/users", "DELETE")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handler.assert_called_once()
