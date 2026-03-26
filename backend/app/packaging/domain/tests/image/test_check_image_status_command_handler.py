from unittest import mock

import assertpy

from app.packaging.domain.command_handlers.image import check_image_status_command_handler
from app.packaging.domain.commands.image import check_image_status_command
from app.packaging.domain.model.image import image
from app.packaging.domain.value_objects.image import image_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


def test_handle_should_return_created_when_image_is_created():
    # ARRANGE
    image_query_service_mock = mock.Mock()

    # Create command
    command = check_image_status_command.CheckImageStatusCommand(
        imageId=image_id_value_object.from_str("image-12345"),
        projectId=project_id_value_object.from_str("project-123"),
    )

    # Mock image
    image_mock = mock.Mock()
    image_mock.status = image.ImageStatus.Created
    image_mock.imageUpstreamId = "image-12345"
    image_query_service_mock.get_image.return_value = image_mock

    # ACT
    result = check_image_status_command_handler.handle(
        command=command,
        image_query_service=image_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["imageStatus"]).is_equal_to(image.ImageStatus.Created.value)
    assertpy.assert_that(result["imageUpstreamId"]).is_equal_to("image-12345")
    image_query_service_mock.get_image.assert_called_once_with(
        project_id=command.projectId.value,
        image_id=command.imageId.value,
    )


def test_handle_should_return_failed_when_image_is_failed():
    # ARRANGE
    image_query_service_mock = mock.Mock()

    # Create command
    command = check_image_status_command.CheckImageStatusCommand(
        imageId=image_id_value_object.from_str("image-12345"),
        projectId=project_id_value_object.from_str("project-123"),
    )

    # Mock image
    image_mock = mock.Mock()
    image_mock.status = image.ImageStatus.Failed
    image_query_service_mock.get_image.return_value = image_mock

    # ACT
    result = check_image_status_command_handler.handle(
        command=command,
        image_query_service=image_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["imageStatus"]).is_equal_to(image.ImageStatus.Failed.value)
    assertpy.assert_that(result["imageUpstreamId"]).is_equal_to("")


def test_handle_should_return_in_progress_when_image_is_creating():
    # ARRANGE
    image_query_service_mock = mock.Mock()

    # Create command
    command = check_image_status_command.CheckImageStatusCommand(
        imageId=image_id_value_object.from_str("image-12345"),
        projectId=project_id_value_object.from_str("project-123"),
    )

    # Mock image
    image_mock = mock.Mock()
    image_mock.status = image.ImageStatus.Creating
    image_query_service_mock.get_image.return_value = image_mock

    # ACT
    result = check_image_status_command_handler.handle(
        command=command,
        image_query_service=image_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["imageStatus"]).is_equal_to(image.ImageStatus.Creating.value)
    assertpy.assert_that(result["imageUpstreamId"]).is_equal_to("")


def test_handle_should_return_failed_when_image_not_found():
    # ARRANGE
    image_query_service_mock = mock.Mock()

    # Create command
    command = check_image_status_command.CheckImageStatusCommand(
        imageId=image_id_value_object.from_str("image-12345"),
        projectId=project_id_value_object.from_str("project-123"),
    )

    # Mock no image found
    image_query_service_mock.get_image.return_value = None

    # ACT
    result = check_image_status_command_handler.handle(
        command=command,
        image_query_service=image_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["imageStatus"]).is_equal_to(image.ImageStatus.Failed.value)
    assertpy.assert_that(result["imageUpstreamId"]).is_equal_to("")
