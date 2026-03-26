from unittest import mock

import assertpy

from app.packaging.domain.commands.image import register_image_command
from app.packaging.domain.model.image import image
from app.packaging.entrypoints.image_builder_event_handler.model import image_builder_image_status
from app.packaging.entrypoints.image_builder_event_handler.tests.conftest import GlobalVariables


@mock.patch(
    "app.packaging.domain.command_handlers.image.register_image_command_handler.handle",
)
def test_image_is_available(
    mock_handler,
    lambda_context,
    generate_event,
    mock_image_query_srv,
    mock_pipeline_query_srv,
):
    # PREPARE
    from app.packaging.entrypoints.image_builder_event_handler import handler

    handler.dependencies.image_query_srv = mock_image_query_srv
    handler.dependencies.pipeline_query_srv = mock_pipeline_query_srv
    minimal_event = generate_event(image_builder_image_status.ImageBuilderImageStatus.Available)

    # ACT
    handler.handler(minimal_event, lambda_context)

    # ASSERT
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    command: register_image_command.RegisterImageCommand = kwargs.get("command")
    assertpy.assert_that(command.imageStatus.value).is_equal_to(image.ImageStatus.Created)
    assertpy.assert_that(command.pipelineId.value).is_equal_to(GlobalVariables.TEST_PIPELINE_ID.value)
    assertpy.assert_that(command.imageBuildVersionArn.value).is_equal_to(GlobalVariables.TEST_BUILD_IMAGE_ARN.value)
    assertpy.assert_that(command.imageUpstreamId.value).is_equal_to(GlobalVariables.TEST_AMI_ID.value)


@mock.patch(
    "app.packaging.domain.command_handlers.image.register_image_command_handler.handle",
)
def test_image_is_failed(
    mock_handler,
    lambda_context,
    generate_event,
    mock_image_query_srv,
    mock_pipeline_query_srv,
):
    # PREPARE
    from app.packaging.entrypoints.image_builder_event_handler import handler

    handler.dependencies.image_query_srv = mock_image_query_srv
    handler.dependencies.pipeline_query_srv = mock_pipeline_query_srv
    minimal_event = generate_event(image_builder_image_status.ImageBuilderImageStatus.Failed)

    # ACT
    handler.handler(minimal_event, lambda_context)

    # ASSERT
    mock_handler.assert_called_once()
    _, kwargs = mock_handler.call_args
    command: register_image_command.RegisterImageCommand = kwargs.get("command")
    assertpy.assert_that(command.imageStatus.value).is_equal_to(image.ImageStatus.Failed)
    assertpy.assert_that(command.pipelineId.value).is_equal_to(GlobalVariables.TEST_PIPELINE_ID.value)
    assertpy.assert_that(command.imageBuildVersionArn.value).is_equal_to(GlobalVariables.TEST_BUILD_IMAGE_ARN.value)
