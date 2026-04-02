import importlib
import json
import logging
from unittest import mock
from urllib.parse import quote

import assertpy
import pytest

from app.projects.adapters.query_services import dynamodb_query_service
from app.projects.domain.commands.enrolments import (
    approve_enrolments_command,
    enrol_user_to_program_command,
)
from app.projects.domain.commands.project_accounts import (
    activate_project_account_command,
    deactivate_project_account_command,
    on_board_project_account_command,
    reonboard_project_account_command,
)
from app.projects.domain.commands.projects import (
    create_project_command,
    update_project_command,
)
from app.projects.domain.commands.technologies import (
    add_technology,
    delete_technology_command,
    update_technology_command,
)
from app.projects.domain.commands.users import (
    assign_user_command,
    reassign_user_command,
    unassign_user_command,
)
from app.projects.domain.model import project_assignment
from app.projects.domain.ports import projects_query_service
from app.projects.entrypoints.api import bootstrapper
from app.projects.entrypoints.api.model import api_model
from app.projects.entrypoints.api.tests import fake_classes
from app.shared.adapters.message_bus import in_memory_command_bus


@pytest.fixture
def mock_command_handlers():
    return {
        on_board_project_account_command.OnBoardProjectAccountCommand: mock.MagicMock(),
        assign_user_command.AssignUserCommand: mock.MagicMock(),
        unassign_user_command.UnAssignUserCommand: mock.MagicMock(),
        reassign_user_command.ReAssignUserCommand: mock.MagicMock(),
        add_technology.AddTechnologyCommand: mock.MagicMock(),
        update_technology_command.UpdateTechnologyCommand: mock.MagicMock(),
        delete_technology_command.DeleteTechnologyCommand: mock.MagicMock(),
        enrol_user_to_program_command.EnrolUserToProgramCommand: mock.MagicMock(),
        approve_enrolments_command.ApproveEnrolmentsCommand: mock.MagicMock(),
        activate_project_account_command.ActivateProjectAccountCommand: mock.MagicMock(),
        deactivate_project_account_command.DeactivateProjectAccountCommand: mock.MagicMock(),
        create_project_command.CreateProjectCommand: mock.MagicMock(),
        update_project_command.UpdateProjectCommand: mock.MagicMock(),
        reonboard_project_account_command.ReonboardProjectAccountCommand: mock.MagicMock(),
    }


@pytest.fixture
def get_mock_dependencies(mock_command_handlers) -> bootstrapper.Dependencies:
    cmd_bus = in_memory_command_bus.InMemoryCommandBus(logger=mock.create_autospec(spec=logging.Logger))
    for command, handler in mock_command_handlers.items():
        cmd_bus.register_handler(command, handler)

    return bootstrapper.Dependencies(
        projects_query_service=fake_classes.FakeProjectsQueryService(),
        enrolment_query_service=fake_classes.FakeEnrolmentsQueryService(),
        technologies_query_service=fake_classes.FakeTechnologiesQueryService(),
        command_bus=cmd_bus,
    )


def test_get_projects(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    minimal_event = authenticated_event(None, "/projects", "GET", {"pageSize": "25"})

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projects)).is_equal_to(5)
    assertpy.assert_that(((response.assignments or [])[0].roles or [])[0]).is_equal_to(
        project_assignment.Role.PLATFORM_USER.value
    )


def test_create_project(lambda_context, authenticated_event, mock_command_handlers, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    request = api_model.CreateProjectRequest(name="Highline", description="Highline project", isActive=True)

    minimal_event = authenticated_event(json.dumps(request.model_dump()), "/projects", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(201)
    mock_command_handlers[create_project_command.CreateProjectCommand].assert_called_once()
    mock_command_handlers[assign_user_command.AssignUserCommand].assert_called_once()


def test_get_project(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "proj-12345"
    minimal_event = authenticated_event(None, f"/projects/{project_id}", "GET")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.project).is_not_none()
    assertpy.assert_that(response.project.projectId).is_equal_to(project_id)


def test_update_project(lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "proj-12345"
    request = api_model.UpdateProjectRequest(name="Highline", description="Highline project", isActive=True)

    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}", "PUT")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handlers[update_project_command.UpdateProjectCommand].assert_called_once()


def test_get_project_accounts(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/accounts", "GET")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAccountsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projectAccounts)).is_equal_to(2)


def test_get_project_accounts_user_account_type(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    account_type = dynamodb_query_service.AccountType.USER.value
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/accounts",
        "GET",
        {"accountType": account_type},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAccountsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projectAccounts)).is_equal_to(1)
    assertpy.assert_that(response.projectAccounts[0].accountType).is_equal_to(account_type)


def test_add_project_account_when_account_is_not_associated_should_associate(
    lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    request = api_model.OnBoardProjectAccountRequest.model_validate(
        {
            "awsAccountId": "001234567890",
            "accountType": "USER",
            "stage": "dev",
            "accountName": "Test",
            "accountDescription": "Description",
            "technologyId": "tech-id-1",
            "region": "us-east-1",
        }
    )
    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/accounts", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handlers[on_board_project_account_command.OnBoardProjectAccountCommand].assert_called_once()


def test_assign_user_should_create_assignment(
    lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    request = api_model.AssignUserRequest.model_validate(
        {"userId": "T0000AA", "roles": [project_assignment.Role.PLATFORM_USER.value]}
    )
    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/users", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handlers[assign_user_command.AssignUserCommand].assert_called_once()


def test_assign_user_should_return_error_when_role_name_invalid(
    lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    request = api_model.AssignUserRequest.model_validate({"userId": "T0000AA", "roles": ["UNKNOWN_ROLE"]})
    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/users", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(400)
    mock_command_handlers[assign_user_command.AssignUserCommand].assert_not_called()


def test_reassign_user_should_update_assignment(
    lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    request = api_model.ReAssignUsersRequest.model_validate({"roles": [project_assignment.Role.PLATFORM_USER.value]})
    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/users", "PUT")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handlers[reassign_user_command.ReAssignUserCommand].assert_called_once()


def test_reassign_user_should_return_error_when_role_name_invalid(
    lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    request = api_model.ReAssignUsersRequest.model_validate({"roles": ["UNKNOWN_ROLE"]})
    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/users", "PUT")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(400)
    mock_command_handlers[reassign_user_command.ReAssignUserCommand].assert_not_called()


def test_unassign_user_should_remove_assignment(
    lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    user_id = "T0000AA"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/users/{user_id}", "DELETE")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handlers[unassign_user_command.UnAssignUserCommand].assert_called_once()


def test_offboard_multiple_users_should_remove_assignments(
    lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    user_id = "T0000AA"
    request = api_model.RemoveUsersRequest(userIds=[user_id]).model_dump_json()
    minimal_event = authenticated_event(request, f"/projects/{project_id}/users", "DELETE")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    mock_command_handlers[unassign_user_command.UnAssignUserCommand].assert_called_once()


def test_get_project_users_should_return_all_users(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/users", "GET")

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
                    "activeDirectoryGroupStatus": "PENDING",
                    "activeDirectoryGroups": [
                        {
                            "domain": "test-domain",
                            "groupName": "test-group",
                        }
                    ],
                    "userEmail": "biff.tannen@example.com",
                }
            ],
            "nextToken": None,
        }
    )


def test_get_user_roles(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "123"
    user_id = "U0"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/users/{user_id}", "GET")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetUserRolesResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.roles)).is_equal_to(2)
    assertpy.assert_that(json.loads(result["body"])).is_equal_to(
        {
            "roles": [
                project_assignment.Role.ADMIN.value,
                project_assignment.Role.PLATFORM_USER.value,
            ],
        }
    )


def test_list_technologies_for_project(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    project_id = "project-id"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/technologies", "GET", {"pageSize": "2"})
    handler.dependencies = get_mock_dependencies
    expected_techs = handler.dependencies.technologies_query_service.list_technologies(
        project_id=project_id, page_size=2
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result.get("statusCode")).is_equal_to(200)
    assertpy.assert_that(json.loads(result["body"])).is_equal_to(
        {
            "nextToken": None,
            "technologies": [api_model.Technology.model_validate(t.model_dump()).model_dump() for t in expected_techs],
        }
    )


def test_add_technology_to_project(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    request = api_model.AddTechnologyRequest(id="tech-1", name="sample-tech").model_dump_json()
    minimal_event = authenticated_event(request, f"/projects/{project_id}/technologies", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)
    # Assert
    assertpy.assert_that(result.get("statusCode")).is_equal_to(200)


def test_update_technology(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    tech_id = "1"
    request = api_model.UpdateTechnologyRequest(name="sample-tech-new").model_dump_json()
    minimal_event = authenticated_event(request, f"/projects/{project_id}/technologies/{tech_id}", "PUT")

    # Act
    result = handler.handler(minimal_event, lambda_context)
    # Assert
    assertpy.assert_that(result.get("statusCode")).is_equal_to(200)


def test_delete_technology(lambda_context, authenticated_event, get_mock_dependencies, mock_command_handlers):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    tech_id = "techn-id"
    minimal_event = authenticated_event(None, f"/projects/{project_id}/technologies/{tech_id}", "DELETE")

    # Act
    result = handler.handler(minimal_event, lambda_context)
    # Assert
    assertpy.assert_that(result.get("statusCode")).is_equal_to(200)
    mock_command_handlers[delete_technology_command.DeleteTechnologyCommand].assert_called_once()


def test_enrol_user_to_project(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies
    project_id = "project-id"
    request = api_model.EnrolUserRequest().model_dump_json()
    minimal_event = authenticated_event(request, f"/projects/{project_id}/enrolments", "POST")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


def test_internal_get_project_accounts(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    minimal_event = authenticated_event(
        None,
        "/internal/accounts",
        "GET",
        {"projectId": project_id, "pageSize": "25"},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAccountsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projectAccounts)).is_equal_to(2)


def test_internal_get_user(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies
    user_id = "user-0"
    minimal_event = authenticated_event(
        None,
        "/internal/user",
        "GET",
        {"userId": user_id},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetUserResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response.user).is_not_none()


def test_internal_get_project_accounts_user_account_type(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    project_id = "project-id"
    account_type = dynamodb_query_service.AccountType.USER.value
    minimal_event = authenticated_event(
        None,
        "/internal/accounts",
        "GET",
        {"accountType": account_type, "projectId": project_id, "pageSize": "25"},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAccountsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projectAccounts)).is_equal_to(1)
    assertpy.assert_that(response.projectAccounts[0].accountType).is_equal_to(account_type)


def test_internal_all_accounts_user_account_type(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    account_type = dynamodb_query_service.AccountType.USER.value
    minimal_event = authenticated_event(
        None,
        "/internal/accounts",
        "GET",
        {"accountType": account_type, "pageSize": "25"},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAccountsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projectAccounts)).is_equal_to(5)
    for accounts in response.projectAccounts:
        assertpy.assert_that(accounts.accountType).is_equal_to(account_type)


def test_internal_all_accounts_user_all_types(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    minimal_event = authenticated_event(
        None,
        "/internal/accounts",
        "GET",
        {"pageSize": "25", "nextToken": None},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAccountsResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projectAccounts)).is_equal_to(5)
    for accounts in response.projectAccounts:
        assertpy.assert_that(accounts.accountType).is_equal_to(
            dynamodb_query_service.AccountType[accounts.accountType].value
        )


def test_internal_can_return_all_projects(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    minimal_event = authenticated_event(
        None,
        "/internal/projects",
        "GET",
        {"pageSize": "25", "nextToken": None},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectsResponse.model_validate_json(result["body"])
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.projects)).is_equal_to(5)


def test_internal_can_return_project_assignments(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    minimal_event = authenticated_event(
        None,
        "/internal/projects/project-id/users",
        "GET",
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAssignmentsResponse.model_validate_json(result["body"])
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.assignments)).is_equal_to(1)


def test_internal_can_return_project_assignments_paged(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    minimal_event = authenticated_event(
        None, "/internal/projects/project-id/users", "GET", query_params={"pageSize": 1}
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAssignmentsResponse.model_validate_json(result["body"])
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.assignments)).is_equal_to(1)


def test_internal_get_user_assignment_when_assignment_exists_returns_data(
    lambda_context, authenticated_event, get_mock_dependencies
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    minimal_event = authenticated_event(
        None,
        "/internal/projects/project-id/users/user-id",
        "GET",
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAssignmentResponse.model_validate_json(result["body"])
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.assignment.userId).is_equal_to("U0")


def test_internal_get_user_assignment_when_assignment_does_not_exist_returns_none(
    lambda_context, authenticated_event, get_mock_dependencies
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies
    handler.dependencies.projects_query_service = mock.create_autospec(projects_query_service.ProjectsQueryService)
    handler.dependencies.projects_query_service.get_user_assignment.return_value = None

    minimal_event = authenticated_event(
        None,
        "/internal/projects/project-id/users/user-id",
        "GET",
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectAssignmentResponse.model_validate_json(result["body"])
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(response.assignment).is_none()


def test_internal_get_user_assignments_count(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies
    user_id = "user-1"

    minimal_event = authenticated_event(
        None,
        "/internal/user/assignments",
        "GET",
        {"pageSize": "25", "nextToken": None, "userId": user_id},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectsResponse.model_validate_json(result["body"])
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.assignments)).is_equal_to(1)


def test_list_enrolments_by_project(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies
    project_id = "project-id"
    minimal_event = authenticated_event(
        None,
        f"/projects/{project_id}/enrolments",
        "GET",
        {"pageSize": "25", "nextToken": None},
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetProjectEnrolmentsResponse.model_validate_json(result["body"])
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.enrolments)).is_equal_to(1)


def test_approve_enrolments_by_project(lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies
    project_id = "project-id"
    request = api_model.UpdateEnrolmentsRequest.model_validate(
        {"enrolmentIds": ["f90a3567-cd73-4ae0-9095-a207ea3b8765"]}
    )
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()), f"/projects/{project_id}/enrolments", "PUT", None
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


@mock.patch(
    "app.projects.domain.command_handlers.project_accounts.activate_project_account_command_handler.handle_activate_project_account_command",
    autospec=True,
)
def test_activate_project_account(command_handler, lambda_context, authenticated_event):
    # Arrange
    from app.projects.entrypoints.api import handler

    importlib.reload(handler)

    project_id = "project-id"
    account_id = "account-id"
    request = api_model.UpdateProjectAccountRequest(accountStatus="Active")
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/accounts/{account_id}",
        "PATCH",
        None,
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    command_handler.assert_called_once()


@mock.patch(
    "app.projects.domain.command_handlers.project_accounts.deactivate_project_account_command_handler.handle_deactivate_project_account_command",
    autospec=True,
)
def test_deactivate_project_account(command_handler, lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    importlib.reload(handler)

    project_id = "project-id"
    account_id = "account-id"
    request = api_model.UpdateProjectAccountRequest(accountStatus="Inactive")
    minimal_event = authenticated_event(
        json.dumps(request.model_dump()),
        f"/projects/{project_id}/accounts/{account_id}",
        "PATCH",
        None,
    )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    command_handler.assert_called_once()


def test_reonboard_project_accounts_should_reonboard_user_accounts(
    authenticated_event, lambda_context, get_mock_dependencies
):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies
    project_id = "project-id"
    account_ids = ["account-id"]
    request = api_model.ReonboardProjectAccountRequest(accountIds=account_ids)
    minimal_event = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/accounts", "PUT")

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)


@pytest.mark.parametrize(
    "token,response_token",
    [
        (None, json.dumps({"PK": "TEST_PAGING_PK", "SK": "TEST_PAGING_SK"})),
        (quote(json.dumps({"string": "SomeStartKey"})), None),
    ],
)
def test_internal_get_all_users(token, response_token, lambda_context, authenticated_event, get_mock_dependencies):
    # Arrange
    from app.projects.entrypoints.api import handler

    handler.dependencies = get_mock_dependencies

    if token:
        minimal_event = authenticated_event(
            None,
            "/internal/users",
            "GET",
            {"pageSize": "25", "nextToken": token},
        )
    else:
        minimal_event = authenticated_event(
            None,
            "/internal/users",
            "GET",
            {"pageSize": "25"},
        )

    # Act
    result = handler.handler(minimal_event, lambda_context)

    # Assert
    assertpy.assert_that(result).is_not_none()
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    response = api_model.GetUsersResponse.model_validate(json.loads(result["body"]))
    assertpy.assert_that(response).is_not_none()
    assertpy.assert_that(len(response.users)).is_equal_to(5)
    assertpy.assert_that(response.nextToken).is_equal_to(response_token)
