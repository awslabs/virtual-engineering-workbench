from unittest import mock

import assertpy

from app.packaging.domain.command_handlers.pipeline import check_pipeline_update_status_command_handler
from app.packaging.domain.commands.pipeline import check_pipeline_update_status_command
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.value_objects.pipeline import pipeline_id_value_object


def test_handle_should_return_created_when_pipeline_exists():
    # ARRANGE
    # Mock dependencies
    pipeline_query_service_mock = mock.Mock()

    # Create command
    command = check_pipeline_update_status_command.CheckPipelineUpdateStatusCommand(
        pipelineId=pipeline_id_value_object.from_str("pipeline-12345"),
    )

    # Mock pipeline
    pipeline_mock = mock.Mock()
    pipeline_mock.status = pipeline.PipelineStatus.Created
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = pipeline_mock

    # ACT
    result = check_pipeline_update_status_command_handler.handle(
        command=command,
        pipeline_query_service=pipeline_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result).is_equal_to({"pipelineUpdateStatus": pipeline.PipelineStatus.Created.value})
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.assert_called_once_with(
        pipeline_id=command.pipelineId.value,
    )


def test_handle_should_return_failed_when_pipeline_not_found():
    # ARRANGE
    # Mock dependencies
    pipeline_query_service_mock = mock.Mock()

    # Create command
    command = check_pipeline_update_status_command.CheckPipelineUpdateStatusCommand(
        pipelineId=pipeline_id_value_object.from_str("pipeline-12345"),
    )

    # Mock pipeline not found
    pipeline_query_service_mock.get_pipeline_by_pipeline_id.return_value = None

    # ACT
    result = check_pipeline_update_status_command_handler.handle(
        command=command,
        pipeline_query_service=pipeline_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result).is_equal_to({"pipelineUpdateStatus": pipeline.PipelineStatus.Failed.value})
