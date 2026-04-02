import assertpy
import pytest

from app.projects.domain.command_handlers.users import assign_user_command_handler as command_handler
from app.projects.domain.commands.users import assign_user_command as command
from app.projects.domain.events.users import user_assigned
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project_assignment
from app.projects.domain.model.project_assignment import Role
from app.projects.domain.value_objects import project_id_value_object, user_id_value_object, user_role_value_object


def test_assign_user_to_project_should_create_assignment(
    handler_dependencies, sample_project, mock_uow_2, mock_assignments_repo
):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0aA"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = None

    # Act
    command_handler.handle_assign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
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


def test_assign_user_to_project_should_uppercase_user_name(
    handler_dependencies, sample_project, mock_uow_2, mock_assignments_repo
):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0aA"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = None

    # Act
    command_handler.handle_assign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
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


def test_assign_user_to_unknown_project_should_raise(handler_dependencies, mock_uow_2):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = None

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        command_handler.handle_assign_user_command(
            cmd=cmd,
            unit_of_work=mock_uow_2,
            projects_query_service=projects_query_service_mock,
            message_bus=message_bus_mock,
        )


def test_assign_already_existing_user_should_raise(
    handler_dependencies, sample_project, user_sample_assignment, mock_uow_2
):
    # Arrange
    cmd = command.AssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_id=user_id_value_object.from_str("u0"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.return_value = user_sample_assignment

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        command_handler.handle_assign_user_command(
            cmd=cmd,
            unit_of_work=mock_uow_2,
            projects_query_service=projects_query_service_mock,
            message_bus=message_bus_mock,
        )
