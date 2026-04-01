import assertpy
import pytest

from app.projects.domain.command_handlers.users import reassign_user_command_handler as command_handler
from app.projects.domain.commands.users import reassign_user_command as command
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model.project_assignment import Role
from app.projects.domain.value_objects import project_id_value_object, user_id_value_object, user_role_value_object


def test_reassign_user_from_user_to_both(
    handler_dependencies,
    sample_project,
    user_sample_assignment,
    both_sample_assignment,
    admin_sample_assignment,
    mock_uow_2,
    mock_assignments_repo,
):
    # Arrange
    cmd = command.ReAssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_ids=[user_id_value_object.from_str("U0"), user_id_value_object.from_str("U2")],
        initiating_user_id=user_id_value_object.from_str("U1"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )

    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.side_effect = [
        admin_sample_assignment,
        user_sample_assignment(),
        user_sample_assignment("U2"),
    ]

    # Act
    command_handler.handle_reassign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
    )

    # Assert
    assertpy.assert_that(message_bus_mock.publish.call_count).is_equal_to(2)
    assertpy.assert_that(mock_assignments_repo.update_entity.call_count).is_equal_to(2)
    pk, ent = mock_assignments_repo.update_entity.call_args.kwargs.values()

    assertpy.assert_that(pk.projectId).is_equal_to(both_sample_assignment().projectId)
    assertpy.assert_that(pk.userId).is_equal_to("U2")
    assertpy.assert_that(ent.roles).contains_only(*both_sample_assignment().roles)

    mock_uow_2.commit.assert_called_once()


def test_reassign_user_from_admin_to_user(
    handler_dependencies,
    sample_project,
    user_sample_assignment,
    admin_sample_assignment,
    mock_uow_2,
    mock_assignments_repo,
):
    # Arrange
    cmd = command.ReAssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_ids=[user_id_value_object.from_str("U0")],
        initiating_user_id=user_id_value_object.from_str("U1"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER)],
    )

    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.side_effect = [admin_sample_assignment, user_sample_assignment()]

    # Act
    command_handler.handle_reassign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
    )

    # Assert
    message_bus_mock.publish.assert_called_once()
    event_obj = message_bus_mock.publish.call_args.args[0]
    event_dict = event_obj.model_dump()

    mock_assignments_repo.update_entity.assert_called_once()
    pk, ent = mock_assignments_repo.update_entity.call_args.kwargs.values()

    assertpy.assert_that(pk.projectId).is_equal_to(user_sample_assignment().projectId)
    assertpy.assert_that(pk.userId).is_equal_to(user_sample_assignment().userId)
    assertpy.assert_that(ent.roles).contains_only(*user_sample_assignment().roles)

    assertpy.assert_that(event_dict["userId"]).is_equal_to("U0")
    assertpy.assert_that(event_dict["projectId"]).is_equal_to("123")
    assertpy.assert_that(event_dict["roles"]).is_equal_to([Role.PLATFORM_USER])

    mock_uow_2.commit.assert_called_once()


def test_reassign_user_to_unknown_project(handler_dependencies, mock_uow_2):
    # Arrange
    cmd = command.ReAssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_ids=[user_id_value_object.from_str("u0")],
        initiating_user_id=user_id_value_object.from_str("U1"),
        roles=[user_role_value_object.from_str(Role.PLATFORM_USER), user_role_value_object.from_str(Role.ADMIN)],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = None

    # Act and Assert
    with pytest.raises(domain_exception.DomainException) as exc_info:
        command_handler.handle_reassign_user_command(
            cmd=cmd,
            unit_of_work=mock_uow_2,
            projects_query_service=projects_query_service_mock,
            message_bus=message_bus_mock,
        )
        assertpy.assert_that(str(exc_info.value)).is_equal_to("Users with IDs: u0 are not assigned to program 123")


def test_reassign_when_user_is_program_owner_should_not_assign_frontend_admins(
    handler_dependencies,
    sample_project,
    user_sample_assignment,
    owner_sample_assignment,
    mock_uow_2,
    mock_assignments_repo,
):
    # Arrange
    cmd = command.ReAssignUserCommand(
        project_id=project_id_value_object.from_str(user_sample_assignment().projectId),
        user_ids=[user_id_value_object.from_str(user_sample_assignment().userId)],
        initiating_user_id=user_id_value_object.from_str(owner_sample_assignment.userId),
        roles=[user_role_value_object.from_str(Role.ADMIN), user_role_value_object.from_str(Role.PROGRAM_OWNER)],
    )

    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.side_effect = [owner_sample_assignment, user_sample_assignment()]

    # Act
    command_handler.handle_reassign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
    )

    # Assert

    mock_assignments_repo.update_entity.assert_called_once()
    pk, ent = mock_assignments_repo.update_entity.call_args.kwargs.values()

    assertpy.assert_that(pk.projectId).is_equal_to(user_sample_assignment().projectId)
    assertpy.assert_that(pk.userId).is_equal_to(user_sample_assignment().userId)
    assertpy.assert_that(ent.roles).contains_only(Role.PROGRAM_OWNER)

    mock_uow_2.commit.assert_called_once()


def test_reassign_when_user_is_program_owner_should_keep_admin_role(
    handler_dependencies,
    sample_project,
    admin_sample_assignment,
    owner_sample_assignment,
    mock_uow_2,
    mock_assignments_repo,
):
    # Arrange
    cmd = command.ReAssignUserCommand(
        project_id=project_id_value_object.from_str(admin_sample_assignment.projectId),
        user_ids=[user_id_value_object.from_str(admin_sample_assignment.userId)],
        initiating_user_id=user_id_value_object.from_str(owner_sample_assignment.userId),
        roles=[
            user_role_value_object.from_str(Role.PLATFORM_USER),
            user_role_value_object.from_str(Role.PROGRAM_OWNER),
        ],
    )

    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.side_effect = [owner_sample_assignment, admin_sample_assignment]

    # Act
    command_handler.handle_reassign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
    )

    # Assert
    mock_assignments_repo.update_entity.assert_called_once()
    pk, ent = mock_assignments_repo.update_entity.call_args.kwargs.values()

    assertpy.assert_that(pk.projectId).is_equal_to(admin_sample_assignment.projectId)
    assertpy.assert_that(pk.userId).is_equal_to(admin_sample_assignment.userId)
    assertpy.assert_that(ent.roles).contains_only(Role.PLATFORM_USER, Role.PROGRAM_OWNER, Role.ADMIN)

    mock_uow_2.commit.assert_called_once()


def test_reassign_when_made_by_service_should_have_admin_as_max_role_boundary(
    handler_dependencies,
    sample_project,
    user_sample_assignment,
    both_sample_assignment,
    mock_uow_2,
    mock_assignments_repo,
):
    # Arrange
    cmd = command.ReAssignUserCommand(
        project_id=project_id_value_object.from_str("123"),
        user_ids=[user_id_value_object.from_str("U0")],
        initiating_user_id=user_id_value_object.from_str("svc-client-id", user_id_value_object.UserIdType.Service),
        roles=[user_role_value_object.from_str(Role.ADMIN)],
    )

    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project
    projects_query_service_mock.get_user_assignment.side_effect = [
        user_sample_assignment(),
    ]

    # Act
    command_handler.handle_reassign_user_command(
        cmd=cmd,
        unit_of_work=mock_uow_2,
        projects_query_service=projects_query_service_mock,
        message_bus=message_bus_mock,
    )

    # Assert
    assertpy.assert_that(message_bus_mock.publish.call_count).is_equal_to(1)
    assertpy.assert_that(mock_assignments_repo.update_entity.call_count).is_equal_to(1)
    pk, ent = mock_assignments_repo.update_entity.call_args.kwargs.values()

    assertpy.assert_that(pk.projectId).is_equal_to(user_sample_assignment().projectId)
    assertpy.assert_that(pk.userId).is_equal_to("U0")
    assertpy.assert_that(ent.roles).contains_only(Role.ADMIN)

    mock_uow_2.commit.assert_called_once()
