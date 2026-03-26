import unittest

import assertpy
import pytest
from freezegun import freeze_time

from app.projects.domain.command_handlers.projects import update_project_command_handler
from app.projects.domain.commands.projects import update_project_command
from app.projects.domain.events.projects import project_updated
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.model import project
from app.projects.domain.value_objects import project_id_value_object
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def mock_command() -> update_project_command.UpdateProjectCommand:
    return update_project_command.UpdateProjectCommand(
        id=project_id_value_object.from_str("proj-12345"),
        name="Highline",
        description="Highline project",
        isActive=True,
    )


@pytest.fixture
def message_bus_mock():
    bus_mock = unittest.mock.create_autospec(spec=message_bus.MessageBus, instance=True)
    return bus_mock


@freeze_time("2012-01-14")
def test_update_project_should_update_project(mock_command, mock_projects_repo, mock_uow_2, message_bus_mock):
    # ASSERT
    project_id = project.ProjectPrimaryKey(projectId="proj-12345")
    proj = project.Project(
        projectId="proj-12345",
        projectName="test-name",
        projectDescription="test-descr",
        isActive=False,
        createDate="2012-01-10T00:00:00+00:00",
        lastUpdateDate="2012-01-10T00:00:00+00:00",
    )
    mock_projects_repo.get.return_value = proj

    # ACT
    update_project_command_handler.handle_update_project_command(
        cmd=mock_command, uow=mock_uow_2, msg_bus=message_bus_mock
    )

    # ASSERT
    mock_projects_repo.get.assert_called_once_with(project_id)
    mock_projects_repo.update_entity.assert_called_once_with(
        pk=project_id,
        entity=project.Project(
            projectId="proj-12345",
            projectName=mock_command.name,
            projectDescription=mock_command.description,
            isActive=mock_command.isActive,
            createDate="2012-01-10T00:00:00+00:00",
            lastUpdateDate="2012-01-14T00:00:00+00:00",
        ),
    )
    mock_uow_2.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once_with(
        project_updated.ProjectUpdated(
            projectId=mock_command.id.value,
            projectName=mock_command.name,
            projectDescription=mock_command.description,
            isActive=mock_command.isActive,
        )
    )


def test_update_project_when_does_not_exist_should_raise(
    mock_command, mock_projects_repo, mock_uow_2, message_bus_mock
):
    # ASSERT
    mock_projects_repo.get.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_project_command_handler.handle_update_project_command(
            cmd=mock_command, uow=mock_uow_2, msg_bus=message_bus_mock
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Project proj-12345 does not exist")
