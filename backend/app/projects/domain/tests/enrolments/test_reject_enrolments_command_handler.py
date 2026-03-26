from unittest import mock

import pytest
from freezegun import freeze_time

from app.projects.domain.command_handlers.enrolments import reject_enrolments_command_handler
from app.projects.domain.commands.enrolments import reject_enrolments_command
from app.projects.domain.events.enrolments import enrolment_rejected
from app.projects.domain.model import enrolment, project
from app.projects.domain.ports import enrolment_query_service, projects_query_service
from app.projects.domain.value_objects import user_id_value_object


@pytest.fixture
def reject_command():
    return reject_enrolments_command.RejectEnrolmentsCommand(
        project_id="proj-123",
        enrolment_ids=["123"],
        rejecter_id=user_id_value_object.from_str("T1100BB"),
        reason="Test",
    )


@pytest.fixture
def enrolment_qs_mock():
    enrolment_qs_mock = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService)
    enrolment_qs_mock.get_enrolment_by_id.return_value = enrolment.Enrolment(
        status=enrolment.EnrolmentStatus.Pending,
        userId="T0011AA",
        userEmail="hari.seldon@example.com",
        projectId="proj-123",
        id="123",
    )  # type: ignore
    yield enrolment_qs_mock


@pytest.fixture
def projects_qs_mock():
    projects_qs_mock = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    projects_qs_mock.get_project_by_id.return_value = project.Project(projectId="proj-123", projectName="Name", isActive=True)  # type: ignore
    projects_qs_mock.get_user_assignment.return_value = None
    yield projects_qs_mock


@freeze_time("2023-03-31")
def test_handle_when_pending_should_set_status_to_rejected_and_approver_name(
    reject_command, mock_uow_2, mock_enrolments_repo, enrolment_qs_mock, projects_qs_mock, message_bus_mock
):
    # ACT
    reject_enrolments_command_handler.handle_reject_enrolments_command(
        cmd=reject_command,
        uow=mock_uow_2,
        enrolment_qry_srv=enrolment_qs_mock,
        project_qry_srv=projects_qs_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    mock_enrolments_repo.update_entity.assert_called_once_with(
        pk=enrolment.EnrolmentPrimaryKey(id="123", projectId=reject_command.project_id),
        entity=enrolment.Enrolment(
            id="123",
            projectId=reject_command.project_id,
            userId="T0011AA",
            userEmail="hari.seldon@example.com",
            status=enrolment.EnrolmentStatus.Rejected,
            approver="T1100BB",
            resolveDate="2023-03-31T00:00:00+00:00",
            lastUpdateDate="2023-03-31T00:00:00+00:00",
            reason="Test",
        ),
    )
    mock_uow_2.commit.assert_called_once()


def test_handle_when_pending_should_publish_event(
    reject_command, mock_uow_2, enrolment_qs_mock, projects_qs_mock, message_bus_mock
):
    # ACT
    reject_enrolments_command_handler.handle_reject_enrolments_command(
        cmd=reject_command,
        uow=mock_uow_2,
        enrolment_qry_srv=enrolment_qs_mock,
        project_qry_srv=projects_qs_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    message_bus_mock.publish.assert_called_with(
        enrolment_rejected.EnrolmentRejected(
            programId="proj-123",
            programName="Name",
            userId="T0011AA",
            userEmail="hari.seldon@example.com",
            enrolmentId="123",
            reason="Test",
        )  # type: ignore
    )
