from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from aws_lambda_powertools.event_handler.exceptions import ForbiddenError

from app.projects.domain.model.service_client_assignment import ServiceClientAssignment, ServiceClientAssignmentStatus
from app.projects.entrypoints.s2s_api.routers import access


def router_with_scopes(scopes):
    return SimpleNamespace(
        current_event={"requestContext": {"authorizer": {"claims": {"scope": scopes}}}},
        context={"user_principal": SimpleNamespace(user_name="caller")},
    )


def assignment(client_id, project_id, status="ACTIVE"):
    return ServiceClientAssignment(
        clientId=client_id,
        projectId=project_id,
        status=status,
        grantedBy="admin",
        createDate="2026-09-01",
        lastUpdateDate="2026-09-01",
    )


def test_ordinary_client_cannot_bootstrap_cross_project():
    query = Mock()
    query.get_service_client_assignment.return_value = None
    router = router_with_scopes("clients/projects/client_assignment.write")
    with pytest.raises(ForbiddenError):
        access.require_bootstrap_or_project_access(router, query, "other-project")
    query.list_service_client_assignments.assert_not_called()


def test_platform_bootstrap_only_recovers_existing_orphan():
    query = Mock()
    query.get_service_client_assignment.return_value = None
    query.get_project_by_id.return_value = object()
    query.list_service_client_assignments.return_value = [assignment("old", "project-1", "REVOKED")]
    router = router_with_scopes("clients/projects/client_assignment.write clients/projects/client_assignment.bootstrap")
    access.require_bootstrap_or_project_access(router, query, "project-1")
    query.list_service_client_assignments.return_value = [assignment("other", "project-1")]
    with pytest.raises(ForbiddenError):
        access.require_bootstrap_or_project_access(router, query, "project-1")
    query.get_project_by_id.return_value = None
    with pytest.raises(ForbiddenError):
        access.require_bootstrap_or_project_access(router, query, "absent-project")


def test_project_access_requires_matching_active_assignment_and_scope():
    query = Mock()
    query.get_service_client_assignment.return_value = assignment(
        "caller", "project-1", ServiceClientAssignmentStatus.REVOKED
    )
    router = router_with_scopes("clients/projects/program.write")
    with pytest.raises(ForbiddenError):
        access.require_project_access(router, query, "project-1", "clients/projects/program.write")
    query.get_service_client_assignment.return_value = assignment("caller", "project-1")
    access.require_project_access(router, query, "project-1", "clients/projects/program.write")
    with pytest.raises(ForbiddenError):
        access.require_project_access(
            router_with_scopes("clients/projects/program.read"),
            query,
            "project-1",
            "clients/projects/program.write",
        )
