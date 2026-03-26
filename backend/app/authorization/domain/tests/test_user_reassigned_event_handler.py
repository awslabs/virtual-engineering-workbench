from unittest import mock

import pytest

from app.authorization.domain.integration_event_handlers.projects import (
    user_reassigned_handler,
)
from app.authorization.domain.integration_events.projects.user_reassigned import (
    UserReAssigned,
)
from app.authorization.domain.read_models import project_assignment
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture
def sample_event():
    return UserReAssigned(
        userId="user-id",
        projectId="project456",
        roles=[project_assignment.Role.PLATFORM_USER],
        groupMemberships=[project_assignment.Group.VEW_USERS],
    )


@pytest.fixture
def mocked_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository)


@pytest.fixture
def mocked_uow(mocked_repo):
    m = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    m.get_repository.return_value = mocked_repo
    return m


def test_should_update_existing_assignment(sample_event, mocked_uow, mocked_repo):
    # ARRANGE
    existing_assignment = project_assignment.Assignment(
        userId=sample_event.userId,
        projectId=sample_event.projectId,
        roles=[project_assignment.Role.ADMIN],
        groupMemberships=[project_assignment.Group.HIL_USERS],
    )
    mocked_repo.get.return_value = existing_assignment

    # ACT
    user_reassigned_handler.handle(sample_event, mocked_uow)

    # ASSERT
    assert existing_assignment.roles == sample_event.roles
    assert existing_assignment.groupMemberships == sample_event.groupMemberships
    mocked_repo.update_entity.assert_called_once()
    mocked_uow.commit.assert_called_once()


def test_should_create_new_assignment(sample_event, mocked_uow, mocked_repo):
    # ARRANGE
    mocked_repo.get.return_value = None

    # ACT
    user_reassigned_handler.handle(sample_event, mocked_uow)

    # ASSERT
    mocked_repo.add.assert_called_once_with(
        project_assignment.Assignment(
            userId=sample_event.userId,
            projectId=sample_event.projectId,
            roles=sample_event.roles,
            groupMemberships=sample_event.groupMemberships,
        )
    )
    mocked_uow.commit.assert_called_once()
