import unittest
from unittest import mock

import pytest
from freezegun import freeze_time

from app.projects.domain.command_handlers.projects import create_project_command_handler
from app.projects.domain.commands.projects import create_project_command
from app.projects.domain.events.projects import project_created
from app.projects.domain.model import project
from app.shared.adapters.message_bus import message_bus


@pytest.fixture()
def mock_command() -> create_project_command.CreateProjectCommand:
    return create_project_command.CreateProjectCommand(name="Highline", description="Highline project", isActive=True)


@pytest.fixture
def message_bus_mock():
    bus_mock = unittest.mock.create_autospec(spec=message_bus.MessageBus, instance=True)
    return bus_mock


@freeze_time("2012-01-14")
@mock.patch("app.projects.domain.model.project.random.choice", lambda chars: "1")
def test_create_project_should_create_project(mock_command, mock_projects_repo, mock_uow_2, message_bus_mock):
    # ACT
    create_project_command_handler.handle_create_project_command(
        cmd=mock_command, uow=mock_uow_2, msg_bus=message_bus_mock
    )

    # ASSERT
    expected_project = project.Project(
        projectId="proj-11111",
        projectName=mock_command.name,
        projectDescription=mock_command.description,
        isActive=mock_command.isActive,
        createDate="2012-01-14T00:00:00+00:00",
        lastUpdateDate="2012-01-14T00:00:00+00:00",
    )
    mock_projects_repo.add.assert_called_once_with(expected_project)
    mock_uow_2.commit.assert_called_once()

    message_bus_mock.publish.assert_called_once_with(
        project_created.ProjectCreated(
            projectId="proj-11111",
            projectName=expected_project.projectName,
            projectDescription=expected_project.projectDescription,
            isActive=expected_project.isActive,
        )
    )
