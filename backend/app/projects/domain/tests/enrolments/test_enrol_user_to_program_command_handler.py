from unittest import mock

import pytest

from app.projects.domain.command_handlers.enrolments import enrol_user_to_program_command_handler as command_handler
from app.projects.domain.commands.enrolments import enrol_user_to_program_command as command
from app.projects.domain.model import enrolment
from app.projects.domain.ports import enrolment_query_service
from app.projects.domain.value_objects import (
    enrolment_id_value_object,
    project_id_value_object,
    source_system_value_object,
    user_email_value_object,
    user_id_value_object,
)


@pytest.fixture
def enrol_user_command():
    return command.EnrolUserToProgramCommand(
        project_id=project_id_value_object.from_str("p-1"),
        user_id=user_id_value_object.from_str("t001"),
        user_email=user_email_value_object.from_str("marty@mcfly.com"),
        source_system=source_system_value_object.from_str("VEW"),
    )


def test_can_put_new_enrolment_for_user_in_project(
    enrol_user_command, mock_uow_2, mock_enrolments_repo, mock_projects_qs, message_bus_mock
):
    # ARRANGE
    enrolment_service = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService, instance=True)
    enrolment_service.list_enrolments_by_user.return_value = ([], None)

    # ACT
    command_handler.handle_enrol_user_to_program_command(
        cmd=enrol_user_command,
        uow=mock_uow_2,
        projects_qry_srv=mock_projects_qs,
        enrolment_qry_srv=enrolment_service,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_enrolments_repo.add.assert_called_once()
    mock_uow_2.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once()


def test_when_user_has_pending_enrolment_does_not_put_enrolment_for_existing_user(
    enrol_user_command, mock_uow_2, mock_enrolments_repo, mock_projects_qs, message_bus_mock
):
    # ARRANGE
    enrolment_service = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService, instance=True)
    enrolment_service.list_enrolments_by_user.return_value = (
        [enrolment.Enrolment(projectId="p-1", userId="t001", status=enrolment.EnrolmentStatus.Pending)],
        None,
    )

    # ACT
    command_handler.handle_enrol_user_to_program_command(
        cmd=enrol_user_command,
        uow=mock_uow_2,
        projects_qry_srv=mock_projects_qs,
        enrolment_qry_srv=enrolment_service,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_enrolments_repo.add.assert_not_called()
    mock_uow_2.commit.assert_not_called()
    message_bus_mock.publish.assert_not_called()


def test_when_user_has_pending_enrolment_for_another_project_creates_new_enrolment(
    enrol_user_command, mock_uow_2, mock_enrolments_repo, mock_projects_qs, message_bus_mock
):
    # ARRANGE
    enrolment_service = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService, instance=True)
    enrolment_service.list_enrolments_by_user.return_value = (
        [enrolment.Enrolment(projectId="p-another", userId="t001", status=enrolment.EnrolmentStatus.Pending)],
        None,
    )

    # ACT
    command_handler.handle_enrol_user_to_program_command(
        cmd=enrol_user_command,
        uow=mock_uow_2,
        projects_qry_srv=mock_projects_qs,
        enrolment_qry_srv=enrolment_service,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_enrolments_repo.add.assert_called_once()
    mock_uow_2.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once()


def test_when_user_has_expired_enrolment_adds_new_enrolment_request(
    enrol_user_command, mock_uow_2, mock_projects_qs, message_bus_mock
):
    # ARRANGE
    enrolment_service = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService, instance=True)
    enrolment_service.list_enrolments_by_user.return_value = ([], None)  # type: ignore

    # ACT
    command_handler.handle_enrol_user_to_program_command(
        cmd=enrol_user_command,
        uow=mock_uow_2,
        projects_qry_srv=mock_projects_qs,
        enrolment_qry_srv=enrolment_service,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    enrolment_service.list_enrolments_by_user.assert_called_once_with(
        user_id="t001", page_size=50, next_token=None, status=enrolment.EnrolmentStatus.Pending
    )


def test_can_use_provided_enrolment_id_when_enrol_user(
    mock_uow_2, mock_enrolments_repo, mock_projects_qs, message_bus_mock
):
    # ARRANGE
    sample_project_id = "p-1"
    sample_user_id = "t001"
    sample_enrolment_id = "e-1"
    cmd = command.EnrolUserToProgramCommand(
        project_id=project_id_value_object.from_str(sample_project_id),
        user_id=user_id_value_object.from_str(sample_user_id),
        user_email=user_email_value_object.from_str("XXXXXXXXXXXXXXX"),
        source_system=source_system_value_object.from_str("RTC"),
        enrolment_id=enrolment_id_value_object.from_str(sample_enrolment_id),
    )

    enrolment_service = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService, instance=True)
    enrolment_service.list_enrolments_by_user.return_value = ([], None)  # type: ignore

    # ACT
    command_handler.handle_enrol_user_to_program_command(
        cmd=cmd,
        uow=mock_uow_2,
        projects_qry_srv=mock_projects_qs,
        enrolment_qry_srv=enrolment_service,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_uow_2.get_repository.assert_called_once()
    assert mock_enrolments_repo.add.call_args[0][0].id == sample_enrolment_id
