from app.projects.domain.command_handlers.technologies import add_technology_command_handler as command_handler
from app.projects.domain.commands.technologies import add_technology as command
from app.projects.domain.value_objects import project_id_value_object


def test_can_add_technology_to_project(handler_dependencies, mock_uow_2, mock_technologies_repo, message_bus_mock):
    # ARRANGE
    cmd = command.AddTechnologyCommand(
        project_id=project_id_value_object.from_str("p-1"), name="tech-1", description="a technology called tech-1"
    )
    (_, projects_query_service_mock, _) = handler_dependencies

    # ACT
    command_handler.handle_add_technology_command(
        cmd=cmd, uow=mock_uow_2, projects_qry_srv=projects_query_service_mock, msg_bus=message_bus_mock
    )

    # ASSERT
    mock_uow_2.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once()
    mock_technologies_repo.add.assert_called_once()
