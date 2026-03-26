from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.tests.conftest import TEST_IMAGE_BUILD_VERSION, TEST_RECIPE_NAME, TEST_RECIPE_VERSION_NAME
from app.packaging.domain.value_objects.image import (
    image_build_version_arn_value_object,
    image_build_version_value_object,
    image_status_value_object,
    image_upstream_id_value_object,
)


def test_image_build_version_value_object_should_parse_image_build_version_arn(get_test_image_build_version):
    # ARRANGE
    image_build_version = get_test_image_build_version

    # ACT
    value_object = image_build_version_value_object.from_int(image_build_version)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(image_build_version)


def test_image_build_version_arn_value_object_should_parse_image_build_version_arn(get_test_image_build_version_arn):
    # ARRANGE
    image_build_version_arn = get_test_image_build_version_arn(
        build_version=TEST_IMAGE_BUILD_VERSION, recipe_name=TEST_RECIPE_NAME, version_name=TEST_RECIPE_VERSION_NAME
    )

    # ACT
    value_object = image_build_version_arn_value_object.from_str(image_build_version_arn)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(image_build_version_arn)


@mock.patch(
    "app.packaging.domain.model.image.image.ImageStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_image_status_value_object_should_parse_image_status():
    # ARRANGE
    status = "TEST_STATUS_1"

    # ACT
    value_object = image_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(status)


@mock.patch(
    "app.packaging.domain.model.image.image.ImageStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_image_status_value_object_should_raise_if_invalid_status():
    # ARRANGE
    status = "TEST_STATUS_INVALID"
    expected_exception_message = "Image status should be in ['TEST_STATUS_1', 'TEST_STATUS_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        image_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_image_upstream_id_value_object_should_parse_image_id():
    # ARRANGE
    image_id = "ami-1234567890abcdefg"

    # ACT
    value_object = image_upstream_id_value_object.from_str(image_id)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(image_id)


def test_image_upstream_id_value_object_should_raise_if_invalid_image_id():
    # ARRANGE
    image_id = "ami-abcdef-12345"
    expected_exception_message = "Image upstream ID must be a valid image ID."

    # ACT
    with pytest.raises(DomainException) as e:
        image_upstream_id_value_object.from_str(image_id)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)
