from unittest import mock

import pytest
from freezegun import freeze_time

from app.projects.domain.command_handlers.enrolments import approve_enrolments_command_handler
from app.projects.domain.commands.enrolments import approve_enrolments_command
from app.projects.domain.events.enrolments import enrolment_approved
from app.projects.domain.model import enrolment, project, project_assignment, user
from app.projects.domain.ports import enrolment_query_service, projects_query_service
from app.projects.domain.value_objects import user_id_value_object


@pytest.fixture
def approve_command():
    return approve_enrolments_command.ApproveEnrolmentsCommand(
        project_id="proj-123",
        enrolment_ids=["123"],
        approver_id=user_id_value_object.from_str("T1100BB"),
    )


@pytest.fixture
def enrolment_qs_mock():
    enrolment_qs_mock = mock.create_autospec(spec=enrolment_query_service.EnrolmentQueryService)
    enrolment_qs_mock.list_enrolments_by_user.return_value = [
        enrolment.Enrolment(
            status=enrolment.EnrolmentStatus.Pending,
            userId="T0011AA",
            projectId="proj-123",
            id="123",
            userEmail="hari.seldon@example.com",
        )
    ], None
    enrolment_qs_mock.get_enrolment_by_id.return_value = enrolment.Enrolment(
        status=enrolment.EnrolmentStatus.Pending,
        userId="T0011AA",
        projectId="proj-123",
        id="123",
        userEmail="hari.seldon@example.com",
    )
    yield enrolment_qs_mock


@pytest.fixture
def projects_qs_mock():
    projects_qs_mock = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    projects_qs_mock.get_project_by_id.return_value = project.Project(projectId="proj-123", projectName="Name", isActive=True)  # type: ignore
    projects_qs_mock.get_user_assignment.return_value = None
    yield projects_qs_mock


def test_handle_when_pending_should_create_new_assignment(
    approve_command, mock_uow_2, mock_assignments_repo, enrolment_qs_mock, projects_qs_mock, message_bus_mock
):
    # ACT
    approve_enrolments_command_handler.handle_approve_enrolments_command(
        cmd=approve_command,
        uow=mock_uow_2,
        enrolment_qry_srv=enrolment_qs_mock,
        project_qry_srv=projects_qs_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    mock_assignments_repo.add.assert_called_once_with(
        project_assignment.Assignment(
            userId="T0011AA",
            userEmail="hari.seldon@example.com",
            projectId=approve_command.project_id,
            roles=[project_assignment.Role.PLATFORM_USER],
            activeDirectoryGroups=[],
            activeDirectoryGroupStatus=user.UserADStatus.PENDING,
        )
    )
    mock_uow_2.commit.assert_called_once()


@freeze_time("2023-03-31")
def test_handle_when_pending_should_set_status_to_approved_and_approver_name(
    approve_command, mock_uow_2, mock_enrolments_repo, enrolment_qs_mock, projects_qs_mock, message_bus_mock
):
    # ACT
    approve_enrolments_command_handler.handle_approve_enrolments_command(
        cmd=approve_command,
        uow=mock_uow_2,
        enrolment_qry_srv=enrolment_qs_mock,
        project_qry_srv=projects_qs_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    mock_enrolments_repo.update_entity.assert_called_once_with(
        pk=enrolment.EnrolmentPrimaryKey(id="123", projectId=approve_command.project_id),
        entity=enrolment.Enrolment(
            id="123",
            projectId=approve_command.project_id,
            userId="T0011AA",
            userEmail="hari.seldon@example.com",
            status=enrolment.EnrolmentStatus.Approved,
            approver="T1100BB",
            resolveDate="2023-03-31T00:00:00+00:00",
            lastUpdateDate="2023-03-31T00:00:00+00:00",
        ),
    )


def test_handle_when_approved_should_publish_events(
    approve_command, mock_uow_2, enrolment_qs_mock, projects_qs_mock, message_bus_mock
):
    # ACT
    approve_enrolments_command_handler.handle_approve_enrolments_command(
        cmd=approve_command,
        uow=mock_uow_2,
        enrolment_qry_srv=enrolment_qs_mock,
        project_qry_srv=projects_qs_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    message_bus_mock.publish.assert_called_once_with(
        enrolment_approved.EnrolmentApproved(
            programId="proj-123",
            programName="Name",
            userId="T0011AA",
            userEmail="hari.seldon@example.com",
            enrolmentId="123",
            roles=[project_assignment.Role.PLATFORM_USER],
        )
    )
