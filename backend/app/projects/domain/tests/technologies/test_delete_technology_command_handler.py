import pytest

from app.projects.domain.command_handlers.technologies import delete_technology_command_handler as command_handler
from app.projects.domain.commands.technologies import delete_technology_command as command
from app.projects.domain.exceptions import domain_exception
from app.projects.domain.value_objects import project_id_value_object, tech_id_value_object


def test_can_delete_technology_from_a_project(
    handler_dependencies, message_bus_mock, mock_uow_2, mock_technologies_repo
):
    # ARRANGE
    cmd = command.DeleteTechnologyCommand(
        project_id=project_id_value_object.from_str("123"),
        id=tech_id_value_object.from_str("tech-abcde"),
    )
    (_, projects_query_service_mock, _) = handler_dependencies
    projects_query_service_mock.list_project_accounts.return_value = None

    # ACT
    command_handler.handle_delete_technology_command(
        cmd=cmd,
        uow=mock_uow_2,
        projects_qry_srv=projects_query_service_mock,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_uow_2.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once()
    mock_technologies_repo.remove.assert_called_once()


def test_delete_technology_with_project_account_should_throw_error(
    handler_dependencies,
    sample_project_account,
    message_bus_mock,
    mock_uow_2,
):
    # ARRANGE
    cmd = command.DeleteTechnologyCommand(
        project_id=project_id_value_object.from_str("123"),
        id=tech_id_value_object.from_str("tech-abcdf"),
    )
    (_, projects_query_service_mock, _) = handler_dependencies
    projects_query_service_mock.list_project_accounts.return_value = sample_project_account

    # Act and Assert
    with pytest.raises(domain_exception.DomainException):
        command_handler.handle_delete_technology_command(
            cmd=cmd,
            uow=mock_uow_2,
            projects_qry_srv=projects_query_service_mock,
            msg_bus=message_bus_mock,
        )
