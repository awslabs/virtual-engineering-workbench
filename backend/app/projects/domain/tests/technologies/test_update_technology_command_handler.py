from unittest import mock

from app.projects.domain.command_handlers.technologies import update_technology_command_handler as command_handler
from app.projects.domain.commands.technologies import update_technology_command as command
from app.projects.domain.ports import technologies_query_service
from app.projects.domain.value_objects import project_id_value_object, tech_id_value_object


def test_can_update_technology_to_project(
    handler_dependencies, sample_technologies, message_bus_mock, mock_uow_2, mock_technologies_repo
):
    # ARRANGE
    cmd = command.UpdateTechnologyCommand(
        project_id=project_id_value_object.from_str("123"),
        id=tech_id_value_object.from_str("tech-abcde"),
        name="technology1",
        description="a technology called tech-1",
    )
    (_, projects_query_service_mock, _) = handler_dependencies
    technologies_query_service_mock = mock.create_autospec(
        spec=technologies_query_service.TechnologiesQueryService, instance=True
    )
    technologies_query_service_mock.list_technologies.return_value = sample_technologies

    # ACT
    command_handler.handle_update_technology_command(
        cmd=cmd,
        uow=mock_uow_2,
        projects_qry_srv=projects_query_service_mock,
        technologies_qry_srv=technologies_query_service_mock,
        msg_bus=message_bus_mock,
    )

    # ASSERT
    mock_uow_2.commit.assert_called_once()
    message_bus_mock.publish.assert_called_once()
    mock_technologies_repo.update_entity.assert_called_once()
