from unittest import mock

import assertpy
import pytest

from app.projects.domain.command_handlers.users import unassign_user_command_handler as command_handler
from app.projects.domain.commands.users import unassign_user_command as command
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import enrolment, project_assignment
from app.projects.domain.ports import enrolment_query_service
from app.projects.domain.value_objects import project_id_value_object, user_id_value_object


@pytest.fixture()
def enrolment_query_service_mock():
    query_service = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService)
    query_service.list_enrolments_by_user.return_value = (
        [enrolment.Enrolment(id="e-123", projectId="project-0000", userId="mock_user", status="Pending")],
        None,
    )
    return query_service


def test_unassign_user_from_project_removes_enrolments_assignments_and_publishes_event(
    handler_dependencies,
    sample_project,
    enrolment_query_service_mock,
    mock_uow_2,
    mock_commit_context,
    mock_assignments_repo,
    mock_enrolments_repo,
):
    # Arrange
    cmd = command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str("p0"),
        user_ids=[user_id_value_object.from_str("u0")],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project

    # Act
    command_handler.handle_unassign_user_command(
        cmd=cmd,
        uow=mock_uow_2,
        projects_qry_service=projects_query_service_mock,
        msg_bus=message_bus_mock,
        enrolment_qry_service=enrolment_query_service_mock,
    )

    # Assert
    message_bus_mock.publish.assert_called_once()
    event_obj = message_bus_mock.publish.call_args.args[0]
    event_dict = event_obj.model_dump()

    assertpy.assert_that(event_dict["userId"]).is_equal_to("u0")
    assertpy.assert_that(event_dict["projectId"]).is_equal_to("p0")

    mock_assignments_repo.remove.assert_called_once_with(
        project_assignment.AssignmentPrimaryKey(userId="u0", projectId="p0")
    )
    mock_enrolments_repo.remove.assert_called_once_with(
        enrolment.EnrolmentPrimaryKey(id="e-123", projectId="project-0000")
    )

    assertpy.assert_that(mock_uow_2.commit.call_count).is_equal_to(1)


def test_unassign_user_from_project_pages_when_fetching_enrolments(
    handler_dependencies,
    sample_project,
    enrolment_query_service_mock,
    mock_uow_2,
):

    # Arrange
    cmd = command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str("p0"),
        user_ids=[user_id_value_object.from_str("u0")],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project
    enrolment_query_service_mock.list_enrolments_by_user.side_effect = [
        (
            [
                enrolment.Enrolment(id=f"{i}", projectId=f"project-{i}", userId="mock_user", status="Pending")
                for i in range(5)
            ],
            "next_token",
        ),
        (
            [
                enrolment.Enrolment(id=f"{i}", projectId=f"project-{i}", userId="mock_user", status="Pending")
                for i in range(5, 10)
            ],
            None,
        ),
    ]

    # Act
    command_handler.handle_unassign_user_command(
        cmd=cmd,
        uow=mock_uow_2,
        projects_qry_service=projects_query_service_mock,
        msg_bus=message_bus_mock,
        enrolment_qry_service=enrolment_query_service_mock,
    )

    # Assert
    enrolment_calls = [
        mock.call(
            user_id="u0",
            page_size=100,
            next_token=None,
            status=enrolment.EnrolmentStatus.Pending,
            project_id="p0",
        ),
        mock.call(
            user_id="u0",
            page_size=100,
            next_token="next_token",
            status=enrolment.EnrolmentStatus.Pending,
            project_id="p0",
        ),
    ]
    enrolment_query_service_mock.list_enrolments_by_user.assert_has_calls(calls=enrolment_calls)


def test_unassign_user_from_project_when_has_more_than_99_enrolments_chunks_removal_operations(
    handler_dependencies,
    sample_project,
    enrolment_query_service_mock,
    mock_uow_2_ca,
    mock_commit_context,
):

    # Arrange
    cmd = command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str("p0"),
        user_ids=[user_id_value_object.from_str("u0")],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project
    enrolment_query_service_mock.list_enrolments_by_user.side_effect = [
        (
            [
                enrolment.Enrolment(id=f"{i}", projectId=f"project-{i}", userId="mock_user", status="Pending")
                for i in range(100)
            ],
            None,
        ),
    ]

    # Act
    command_handler.handle_unassign_user_command(
        cmd=cmd,
        uow=mock_uow_2_ca,
        projects_qry_service=projects_query_service_mock,
        msg_bus=message_bus_mock,
        enrolment_qry_service=enrolment_query_service_mock,
    )

    # Assert
    assertpy.assert_that(mock_commit_context).is_length(2)
    assertpy.assert_that(mock_commit_context[0][project_assignment.Assignment]["remove"]).is_length(1)
    assertpy.assert_that(mock_commit_context[1][project_assignment.Assignment]["remove"]).is_length(1)

    assertpy.assert_that(mock_commit_context[0][enrolment.Enrolment]["remove"]).is_length(99)
    assertpy.assert_that(mock_commit_context[1][enrolment.Enrolment]["remove"]).is_length(1)

    assertpy.assert_that(mock_uow_2_ca.commit.call_count).is_equal_to(2)


def test_unassign_user_from_project_when_has_multiple_users_chunks_removal_operations(
    handler_dependencies,
    sample_project,
    enrolment_query_service_mock,
    mock_uow_2_ca,
    mock_commit_context,
):

    # Arrange
    cmd = command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str("p0"),
        user_ids=[user_id_value_object.from_str("u0"), user_id_value_object.from_str("u1")],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project
    enrolment_query_service_mock.list_enrolments_by_user.return_value = (
        [enrolment.Enrolment(id="e-123", projectId="project-0000", userId="mock_user", status="Pending")],
        None,
    )

    # Act
    command_handler.handle_unassign_user_command(
        cmd=cmd,
        uow=mock_uow_2_ca,
        projects_qry_service=projects_query_service_mock,
        msg_bus=message_bus_mock,
        enrolment_qry_service=enrolment_query_service_mock,
    )

    # Assert
    assertpy.assert_that(mock_commit_context).is_length(1)

    assertpy.assert_that(mock_commit_context[0][project_assignment.Assignment]["remove"]).is_length(2)
    assertpy.assert_that(mock_commit_context[0][enrolment.Enrolment]["remove"]).is_length(2)

    assertpy.assert_that(mock_uow_2_ca.commit.call_count).is_equal_to(1)

    assertpy.assert_that(message_bus_mock.publish.call_count).is_equal_to(2)


def test_unassign_user_from_project_when_has_multiple_users_and_enrollments_chunks_removal_operations(
    handler_dependencies,
    sample_project,
    enrolment_query_service_mock,
    mock_uow_2_ca,
    mock_commit_context,
):

    # Arrange
    cmd = command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str("p0"),
        user_ids=[user_id_value_object.from_str("u0"), user_id_value_object.from_str("u1")],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies
    projects_query_service_mock.get_project_by_id.return_value = sample_project
    enrolment_query_service_mock.list_enrolments_by_user.return_value = (
        [
            enrolment.Enrolment(id=f"{i}", projectId=f"project-{i}", userId="mock_user", status="Pending")
            for i in range(50)
        ],
        None,
    )

    # Act
    command_handler.handle_unassign_user_command(
        cmd=cmd,
        uow=mock_uow_2_ca,
        projects_qry_service=projects_query_service_mock,
        msg_bus=message_bus_mock,
        enrolment_qry_service=enrolment_query_service_mock,
    )

    # Assert
    assertpy.assert_that(mock_commit_context).is_length(2)

    assertpy.assert_that(mock_commit_context[0][project_assignment.Assignment]["remove"]).is_length(1)
    assertpy.assert_that(mock_commit_context[0][enrolment.Enrolment]["remove"]).is_length(50)
    assertpy.assert_that(mock_commit_context[1][project_assignment.Assignment]["remove"]).is_length(1)
    assertpy.assert_that(mock_commit_context[1][enrolment.Enrolment]["remove"]).is_length(50)

    assertpy.assert_that(mock_uow_2_ca.commit.call_count).is_equal_to(2)


def test_unassign_user_from_unknown_project_raises(
    handler_dependencies,
    enrolment_query_service_mock,
    mock_uow_2,
):
    # Arrange
    cmd = command.UnAssignUserCommand(
        project_id=project_id_value_object.from_str("p0"),
        user_ids=[user_id_value_object.from_str("u0")],
    )
    (_, projects_query_service_mock, message_bus_mock) = handler_dependencies

    projects_query_service_mock.get_project_by_id.return_value = None

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        command_handler.handle_unassign_user_command(
            cmd=cmd,
            uow=mock_uow_2,
            projects_qry_service=projects_query_service_mock,
            enrolment_qry_service=enrolment_query_service_mock,
            msg_bus=message_bus_mock,
        )
