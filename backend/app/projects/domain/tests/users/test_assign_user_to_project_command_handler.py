from unittest import mock

import assertpy
import pytest

from app.projects.domain.command_handlers.users import assign_user_command_handler as command_handler
from app.projects.domain.commands.users import assign_user_command as command
from app.projects.domain.events.users import user_assigned
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_assignment
from app.projects.domain.model.project_assignment import Role
from app.projects.domain.ports import user_directory_service
from app.projects.domain.value_objects import project_id_value_object, user_id_value_object, user_role_value_object


@pytest.fixture
def user_directory_service_mock():
    svc = mock.create_autospec(spec=user_directory_service.UserDirectoryService, instance=True)
    svc.get_user_email.return_value = None
    return svc


def test_assign_user_to_project_should_create_assignment(
    handler_dependencies, sample_project, mock_uow_2, mock_assignments_repo, user_directory_service_mock
):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0aA"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    _, projects_query_service_mock, message_bus_mock = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = None

    # Act
    command_handler.handle_assign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
        user_directory_service=user_directory_service_mock,
    )

    # Assert
    message_bus_mock.publish.assert_called_once_with(
        user_assigned.UserAssigned(
            projectId=project_id_value_object.from_str("123").value,
            userId=user_id_value_object.from_str("U0AA").value,
            roles=[
                user_role_value_object.from_str(Role.PLATFORM_USER).value,
                user_role_value_object.from_str(Role.ADMIN).value,
            ],
        )
    )
    mock_uow_2.commit.assert_called_once()

    mock_assignments_repo.add.assert_called_once_with(
        project_assignment.Assignment(
            userId="U0AA",
            projectId="123",
            roles=["PLATFORM_USER", "ADMIN"],
            userEmail=None,
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus="PENDING",
        )
    )


def test_assign_user_to_project_should_populate_email_from_directory(
    handler_dependencies, sample_project, mock_uow_2, mock_assignments_repo, user_directory_service_mock
):
    # Arrange: the identity provider knows the user's email
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0aA"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER)],
    )
    _, projects_query_service_mock, message_bus_mock = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = None
    user_directory_service_mock.get_user_email.return_value = "user@example.com"

    # Act
    command_handler.handle_assign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
        user_directory_service=user_directory_service_mock,
    )

    # Assert: handler looked up by the uppercased, canonical user_tid
    user_directory_service_mock.get_user_email.assert_called_once_with("U0AA")

    # Assert: persisted assignment carries the email
    persisted_assignment = mock_assignments_repo.add.call_args.args[0]
    assertpy.assert_that(persisted_assignment.userEmail).is_equal_to("user@example.com")
    assertpy.assert_that(persisted_assignment.userId).is_equal_to("U0AA")


def test_assign_user_to_project_should_persist_when_email_lookup_returns_none(
    handler_dependencies, sample_project, mock_uow_2, mock_assignments_repo, user_directory_service_mock
):
    # Arrange: the IdP has no record of the user (or lookup failed).
    # The handler must still complete the assignment — a missing email must
    # not block user onboarding.
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0aA"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER)],
    )
    _, projects_query_service_mock, message_bus_mock = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = None
    user_directory_service_mock.get_user_email.return_value = None

    # Act
    command_handler.handle_assign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
        user_directory_service=user_directory_service_mock,
    )

    # Assert: assignment persisted with userEmail=None
    persisted_assignment = mock_assignments_repo.add.call_args.args[0]
    assertpy.assert_that(persisted_assignment.userEmail).is_none()
    mock_uow_2.commit.assert_called_once()


def test_assign_user_to_project_should_uppercase_user_name(
    handler_dependencies, sample_project, mock_uow_2, mock_assignments_repo, user_directory_service_mock
):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0aA"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    _, projects_query_service_mock, message_bus_mock = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = None

    # Act
    command_handler.handle_assign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
        user_directory_service=user_directory_service_mock,
    )

    # Assert
    message_bus_mock.publish.assert_called_once_with(
        user_assigned.UserAssigned(
            projectId=project_id_value_object.from_str("123").value,
            userId=user_id_value_object.from_str("U0AA").value,
            roles=[
                user_role_value_object.from_str(Role.PLATFORM_USER).value,
                user_role_value_object.from_str(Role.ADMIN).value,
            ],
        )
    )

    assignment_dict = mock_assignments_repo.add.call_args.args[0].model_dump()
    assertpy.assert_that(assignment_dict["userId"]).is_equal_to("U0AA")


def test_assign_user_to_unknown_project_should_raise(handler_dependencies, mock_uow_2, user_directory_service_mock):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    _, projects_query_service_mock, message_bus_mock = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = None

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        command_handler.handle_assign_user_command(
            cmd=cmd,
            unit_of_work=mock_uow_2,
            projects_query_service=projects_query_service_mock,
            message_bus=message_bus_mock,
            user_directory_service=user_directory_service_mock,
        )


def test_assign_already_existing_user_should_raise(
    handler_dependencies, sample_project, user_sample_assignment, mock_uow_2, user_directory_service_mock
):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    _, projects_query_service_mock, message_bus_mock = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = user_sample_assignment

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        command_handler.handle_assign_user_command(
            cmd=cmd,
            unit_of_work=mock_uow_2,
            projects_query_service=projects_query_service_mock,
            message_bus=message_bus_mock,
            user_directory_service=user_directory_service_mock,
        )
