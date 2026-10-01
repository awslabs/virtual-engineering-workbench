from unittest import mock

import pytest
from freezegun import freeze_time

from app.projects.domain.command_handlers.service_clients import (
    put_service_client_assignment_command_handler,
    revoke_service_client_assignment_command_handler,
)
from app.projects.domain.commands.service_clients.put_service_client_assignment_command import (
    PutServiceClientAssignmentCommand,
)
from app.projects.domain.commands.service_clients.revoke_service_client_assignment_command import (
    RevokeServiceClientAssignmentCommand,
)
from app.projects.domain.model import service_client_assignment
from app.projects.domain.ports import projects_query_service
from app.projects.domain.value_objects import project_id_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture
def assignment_repository():
    return mock.create_autospec(unit_of_work.GenericRepository, instance=True)


@pytest.fixture
def uow(assignment_repository):
    result = mock.create_autospec(unit_of_work.UnitOfWork, instance=True)
    result.get_repository.return_value = assignment_repository
    return result


@pytest.fixture
def query_service():
    return mock.create_autospec(projects_query_service.ProjectsQueryService, instance=True)


def assignment(status: service_client_assignment.ServiceClientAssignmentStatus):
    return service_client_assignment.ServiceClientAssignment(
        clientId="terraform-prod",
        projectId="proj-1",
        status=status,
        grantedBy="bootstrap-client",
        createDate="2026-09-15T08:00:00+00:00",
        lastUpdateDate="2026-09-15T08:00:00+00:00",
    )


def put_command(granted_by: str = "bootstrap-client"):
    return PutServiceClientAssignmentCommand(
        project_id=project_id_value_object.from_str("proj-1"),
        client_id="terraform-prod",
        granted_by=granted_by,
    )


def revoke_command():
    return RevokeServiceClientAssignmentCommand(
        project_id=project_id_value_object.from_str("proj-1"),
        client_id="terraform-prod",
        revoked_by="bootstrap-client",
    )


@freeze_time("2026-09-16T10:00:00+00:00")
def test_put_assignment_creates_active_assignment(uow, assignment_repository, query_service):
    query_service.get_service_client_assignment.return_value = None

    put_service_client_assignment_command_handler.handle_put_service_client_assignment_command(
        put_command(), uow=uow, projects_query_service=query_service
    )

    saved = assignment_repository.add.call_args.args[0]
    assert saved.clientId == "terraform-prod"
    assert saved.projectId == "proj-1"
    assert saved.status == service_client_assignment.ServiceClientAssignmentStatus.ACTIVE
    assert saved.grantedBy == "bootstrap-client"
    assert saved.createDate == "2026-09-16T10:00:00+00:00"
    assert saved.lastUpdateDate == "2026-09-16T10:00:00+00:00"
    uow.commit.assert_called_once_with()


def test_put_active_assignment_is_idempotent(uow, assignment_repository, query_service):
    query_service.get_service_client_assignment.return_value = assignment(
        service_client_assignment.ServiceClientAssignmentStatus.ACTIVE
    )

    put_service_client_assignment_command_handler.handle_put_service_client_assignment_command(
        put_command(), uow=uow, projects_query_service=query_service
    )

    assignment_repository.add.assert_not_called()
    assignment_repository.update_entity.assert_not_called()
    uow.commit.assert_not_called()


@freeze_time("2026-09-16T10:00:00+00:00")
def test_put_revoked_assignment_reactivates_it(uow, assignment_repository, query_service):
    existing = assignment(service_client_assignment.ServiceClientAssignmentStatus.REVOKED)
    query_service.get_service_client_assignment.return_value = existing

    put_service_client_assignment_command_handler.handle_put_service_client_assignment_command(
        put_command(granted_by="replacement-admin"),
        uow=uow,
        projects_query_service=query_service,
    )

    key, updated = assignment_repository.update_entity.call_args.args
    assert key == service_client_assignment.ServiceClientAssignmentPrimaryKey(
        clientId="terraform-prod", projectId="proj-1"
    )
    assert updated.status == service_client_assignment.ServiceClientAssignmentStatus.ACTIVE
    assert updated.grantedBy == "replacement-admin"
    assert updated.createDate == "2026-09-15T08:00:00+00:00"
    assert updated.lastUpdateDate == "2026-09-16T10:00:00+00:00"
    uow.commit.assert_called_once_with()


@freeze_time("2026-09-16T10:00:00+00:00")
def test_revoke_active_assignment_marks_it_revoked(uow, assignment_repository, query_service):
    existing = assignment(service_client_assignment.ServiceClientAssignmentStatus.ACTIVE)
    query_service.get_service_client_assignment.return_value = existing

    revoke_service_client_assignment_command_handler.handle_revoke_service_client_assignment_command(
        revoke_command(), uow=uow, projects_query_service=query_service
    )

    key, updated = assignment_repository.update_entity.call_args.args
    assert key == service_client_assignment.ServiceClientAssignmentPrimaryKey(
        clientId="terraform-prod", projectId="proj-1"
    )
    assert updated.status == service_client_assignment.ServiceClientAssignmentStatus.REVOKED
    assert updated.grantedBy == "bootstrap-client"
    assert updated.lastUpdateDate == "2026-09-16T10:00:00+00:00"
    uow.commit.assert_called_once_with()


def test_revoke_assignment_is_idempotent(uow, assignment_repository, query_service):
    query_service.get_service_client_assignment.return_value = assignment(
        service_client_assignment.ServiceClientAssignmentStatus.REVOKED
    )

    revoke_service_client_assignment_command_handler.handle_revoke_service_client_assignment_command(
        revoke_command(), uow=uow, projects_query_service=query_service
    )

    assignment_repository.update_entity.assert_not_called()
    uow.commit.assert_not_called()
