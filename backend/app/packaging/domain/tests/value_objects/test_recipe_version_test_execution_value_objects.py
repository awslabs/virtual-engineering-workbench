from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_command_id_value_object,
    recipe_version_test_execution_command_status_value_object,
    recipe_version_test_execution_id_value_object,
    recipe_version_test_execution_instance_id_value_object,
    recipe_version_test_execution_instance_status_value_object,
)


@mock.patch("uuid.UUID", mock.MagicMock())
def test_recipe_version_test_execution_command_id_value_object_should_parse_command_id():
    # ARRANGE
    command_id = "command-id-00000000"

    # ACT
    value_object = recipe_version_test_execution_command_id_value_object.from_str(command_id)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(command_id)


@mock.patch("uuid.UUID", mock.MagicMock(side_effect=ValueError()))
def test_recipe_version_test_execution_command_id_value_object_should_raise_if_command_id_not_uuid():
    # ARRANGE
    command_id = "command-id-00000000"
    expected_exception_message = "Command ID is not a valid UUID."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_test_execution_command_id_value_object.from_str(command_id)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_recipe_version_test_execution_command_status_value_object_should_parse_status():
    # ARRANGE
    status = "TEST_STATUS_1"

    # ACT
    value_object = recipe_version_test_execution_command_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(status)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_recipe_version_test_execution_command_status_value_object_should_raise_if_invalid_status():
    # ARRANGE
    status = "TEST_STATUS_INVALID"
    expected_exception_message = "Command status should be in ['TEST_STATUS_1', 'TEST_STATUS_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_test_execution_command_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch("uuid.UUID", mock.MagicMock())
def test_recipe_version_test_execution_id_value_object_should_parse_execution_id():
    # ARRANGE
    execution_id = "execution-id-00000000"

    # ACT
    value_object = recipe_version_test_execution_id_value_object.from_str(execution_id)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(execution_id)


@mock.patch("uuid.UUID", mock.MagicMock(side_effect=ValueError()))
def test_recipe_version_test_execution_id_value_object_should_raise_if_execution_id_not_uuid():
    # ARRANGE
    execution_id = "execution-id-00000000"
    expected_exception_message = "Recipe version test execution ID is not a valid UUID."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_test_execution_id_value_object.from_str(execution_id)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_version_test_execution_instance_id_value_object_should_parse_image_id():
    # ARRANGE
    instance_id = "i-1234567890abcdefg"

    # ACT
    value_object = recipe_version_test_execution_instance_id_value_object.from_str(instance_id)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(instance_id)


def test_recipe_version_test_execution_instance_id_value_object_should_raise_if_invalid_instance_id():
    # ARRANGE
    instance_id = "i-abcdef-12345"
    expected_exception_message = "Recipe version test execution instance ID must be a valid instance ID."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_test_execution_instance_id_value_object.from_str(instance_id)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_recipe_version_test_execution_instance_status_value_object_should_parse_status():
    # ARRANGE
    status = "TEST_STATUS_1"

    # ACT
    value_object = recipe_version_test_execution_instance_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(status)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version_test_execution.RecipeVersionTestExecutionInstanceStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_recipe_version_test_execution_instance_status_value_object_should_raise_if_invalid_status():
    # ARRANGE
    status = "TEST_STATUS_INVALID"
    expected_exception_message = (
        "Recipe version test execution instance status should be in ['TEST_STATUS_1', 'TEST_STATUS_2']."
    )

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_test_execution_instance_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)
