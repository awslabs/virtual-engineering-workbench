from unittest import mock

import pytest

from app.authorization.domain.command_handlers import sync_assignments_command_handler
from app.authorization.domain.commands import sync_assignments_command
from app.authorization.domain.ports import (
    assignments_query_service,
    projects_query_service,
)
from app.authorization.domain.read_models import project, project_assignment
from app.shared.adapters.boto import paging_utils
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture
def mocked_projects():
    return [
        project.Project(projectId="proj-123"),
        project.Project(projectId="proj-456"),
        project.Project(projectId="proj-789"),
    ]


@pytest.fixture
def mocked_project_assignments():
    return {
        "proj-123": [
            project_assignment.Assignment(
                projectId="proj-123",
                userId="uid-123",
                roles=[project_assignment.Role.ADMIN],
                userEmail="test@example.doesnotexist",
                activeDirectoryGroups=[{"a": "b"}],
                groupMemberships=["VEW_USERS"],
            ),
            project_assignment.Assignment(
                projectId="proj-123",
                userId="uid-456",
                roles=[project_assignment.Role.PLATFORM_USER],
                userEmail="test2@example.doesnotexist",
                activeDirectoryGroups=[{"c": "d"}],
                groupMemberships=["VEW_USERS"],
            ),
        ],
        "proj-456": [
            project_assignment.Assignment(
                projectId="proj-456",
                userId="uid-123",
                roles=[project_assignment.Role.ADMIN],
                userEmail="test@example.doesnotexist",
                activeDirectoryGroups=[{"a": "b"}],
                groupMemberships=["VEW_USERS"],
            ),
        ],
        "proj-789": [
            project_assignment.Assignment(
                projectId="proj-789",
                userId="uid-123",
                roles=[project_assignment.Role.ADMIN],
                userEmail="test@example.doesnotexist",
                activeDirectoryGroups=[{"a": "b"}],
                groupMemberships=["VEW_USERS"],
            ),
            project_assignment.Assignment(
                projectId="proj-789",
                userId="uid-456",
                roles=[project_assignment.Role.PLATFORM_USER],
                userEmail="test2@example.doesnotexist",
                activeDirectoryGroups=[{"c": "d"}],
                groupMemberships=["VEW_USERS"],
            ),
        ],
    }


@pytest.fixture
def mocked_auth_assignments():
    return {
        "proj-123": [
            project_assignment.Assignment(
                projectId="proj-123",
                userId="uid-456",
                roles=[project_assignment.Role.PLATFORM_USER],
                userEmail="test2@example.doesnotexist",
                activeDirectoryGroups=[{"c": "d"}],
            ),
        ],
        "proj-456": [
            project_assignment.Assignment(
                projectId="proj-456",
                userId="uid-123",
                roles=[project_assignment.Role.ADMIN],
                userEmail="test@example.doesnotexist",
                activeDirectoryGroups=[{"a": "b"}],
            ),
            project_assignment.Assignment(
                projectId="proj-456",
                userId="uid-456",
                roles=[project_assignment.Role.PLATFORM_USER],
                userEmail="test2@example.doesnotexist",
                activeDirectoryGroups=[{"c": "d"}],
            ),
        ],
        "proj-789": [
            project_assignment.Assignment(
                projectId="proj-789",
                userId="uid-123",
                roles=[project_assignment.Role.PRODUCT_CONTRIBUTOR],
                userEmail="test@example.doesnotexist",
                activeDirectoryGroups=[{"a": "b"}],
            ),
            project_assignment.Assignment(
                projectId="proj-789",
                userId="uid-456",
                roles=[project_assignment.Role.PLATFORM_USER],
                userEmail="test2@example.doesnotexist",
                activeDirectoryGroups=[{"e": "f"}],
            ),
        ],
    }


@pytest.fixture
def mocked_projects_qs(mocked_projects, mocked_project_assignments):
    m = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)

    def __get_projects(page: paging_utils.PageInfo):
        if page.page_token is None:
            return paging_utils.PagedResponse(items=[mocked_projects[0]], page_token=1)
        else:
            return paging_utils.PagedResponse(
                items=[mocked_projects[page.page_token]],
                page_token=page.page_token + 1 if page.page_token + 1 < len(mocked_projects) else None,
            )

    def __get_project_assignments(project_id: str, page: paging_utils.PageInfo):
        project_assignments = mocked_project_assignments.get(project_id)
        if page.page_token is None:
            return paging_utils.PagedResponse(
                items=[project_assignments[0]], page_token=1 if len(project_assignments) > 1 else None
            )
        else:
            return paging_utils.PagedResponse(
                items=[project_assignments[page.page_token]],
                page_token=page.page_token + 1 if page.page_token + 1 < len(project_assignments) else None,
            )

    m.get_projects.side_effect = __get_projects
    m.get_project_assignments.side_effect = __get_project_assignments
    return m


@pytest.fixture
def mocked_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository)


@pytest.fixture
def mocked_uow(mocked_repo):
    m = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    m.get_repository.return_value = mocked_repo
    return m


@pytest.fixture
def mocked_assignments_qs(mocked_auth_assignments):
    m = mock.create_autospec(spec=assignments_query_service.AssignmentsQueryService)

    def __get_project_assignments(project_id: str):
        return mocked_auth_assignments.get(project_id)

    m.get_project_assignments.side_effect = __get_project_assignments
    return m


def test_when_has_new_assignments_should_store_in_db(
    mocked_projects_qs, mocked_assignments_qs, mocked_uow, mocked_repo, mock_logger
):
    # ARRANGE

    # ACT
    sync_assignments_command_handler.handle(
        command=sync_assignments_command.SyncAssignmentsCommand(),
        projects_qs=mocked_projects_qs,
        assignments_qs=mocked_assignments_qs,
        uow=mocked_uow,
        logger=mock_logger,
    )

    # ASSERT
    mocked_repo.add.assert_called_once_with(
        project_assignment.Assignment(
            userId="uid-123",
            projectId="proj-123",
            roles=[project_assignment.Role.ADMIN],
            userEmail="test@example.doesnotexist",
            activeDirectoryGroups=[{"a": "b"}],
            groupMemberships=["VEW_USERS"],
        )
    )
    mocked_uow.commit.assert_called()


def test_when_assignments_removed_should_remove_from_db(
    mocked_projects_qs, mocked_assignments_qs, mocked_uow, mocked_repo, mock_logger
):
    # ARRANGE

    # ACT
    sync_assignments_command_handler.handle(
        command=sync_assignments_command.SyncAssignmentsCommand(),
        projects_qs=mocked_projects_qs,
        assignments_qs=mocked_assignments_qs,
        uow=mocked_uow,
        logger=mock_logger,
    )

    # ASSERT
    mocked_repo.remove.assert_called_once_with(
        project_assignment.AssignmentPrimaryKey(userId="uid-456", projectId="proj-456")
    )
    mocked_uow.commit.assert_called()


def test_when_assignments_changed_should_update_in_db(
    mocked_projects_qs, mocked_assignments_qs, mocked_uow, mocked_repo, mock_logger
):
    # ARRANGE

    # ACT
    sync_assignments_command_handler.handle(
        command=sync_assignments_command.SyncAssignmentsCommand(),
        projects_qs=mocked_projects_qs,
        assignments_qs=mocked_assignments_qs,
        uow=mocked_uow,
        logger=mock_logger,
    )

    # ASSERT
    mocked_repo.update_entity.assert_any_call(
        project_assignment.AssignmentPrimaryKey(userId="uid-123", projectId="proj-789"),
        project_assignment.Assignment(
            userId="uid-123",
            projectId="proj-789",
            roles=[project_assignment.Role.ADMIN],
            userEmail="test@example.doesnotexist",
            activeDirectoryGroups=[{"a": "b"}],
            groupMemberships=["VEW_USERS"],
        ),
    )
    mocked_uow.commit.assert_called()
