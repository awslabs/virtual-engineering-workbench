from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.model.shared.component_version_entry import ComponentVersionEntry
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_arn_value_object,
    recipe_version_components_versions_value_object,
    recipe_version_description_value_object,
    recipe_version_parent_image_upstream_id_value_object,
    recipe_version_release_type_value_object,
    recipe_version_status_value_object,
    recipe_version_volume_size_value_object,
)


def test_recipe_version_components_versions_value_object_should_parse_components_versions():
    # ARRANGE
    components_versions = [
        ComponentVersionEntry(
            componentId="comp-00000000",
            componentName="test-component-00000000",
            componentVersionId="vers-00000000",
            componentVersionName="1.0.0",
            componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
            order=1,
        ),
        ComponentVersionEntry(
            componentId="comp-00000001",
            componentName="test-component-00000001",
            componentVersionId="vers-00000001",
            componentVersionName="1.0.0",
            componentVersionType=component_version_entry.ComponentVersionEntryType.Main.value,
            order=2,
        ),
    ]

    # ACT
    value_object = recipe_version_components_versions_value_object.from_list(components_versions)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(components_versions)


@pytest.mark.parametrize(
    "components_versions,expected_exception_message",
    (
        (
            [
                ComponentVersionEntry(
                    componentId="",
                    componentName="test-component-00000000",
                    componentVersionId="vers-00000000",
                    componentVersionName="1.0.0",
                    order=1,
                ),
            ],
            "Component ID cannot be empty.",
        ),
        (
            [
                ComponentVersionEntry(
                    componentId="comp-00000000",
                    componentName="",
                    componentVersionId="vers-00000000",
                    componentVersionName="1.0.0",
                    order=1,
                ),
            ],
            "Component name cannot be empty.",
        ),
        (
            [
                ComponentVersionEntry(
                    componentId="comp-00000000",
                    componentName="test-component-00000000",
                    componentVersionId="",
                    componentVersionName="1.0.0",
                    order=1,
                ),
            ],
            "Component version ID cannot be empty.",
        ),
        (
            [
                ComponentVersionEntry(
                    componentId="comp-00000000",
                    componentName="test-component-00000000",
                    componentVersionId="vers-00000000",
                    componentVersionName="",
                    order=1,
                ),
            ],
            "Component version name cannot be empty.",
        ),
        (
            [
                ComponentVersionEntry(
                    componentId="comp-00000000",
                    componentName="test-component-00000000",
                    componentVersionId="vers-00000000",
                    componentVersionName="1.0.0",
                ),
            ],
            "Order cannot be empty.",
        ),
    ),
)
def test_recipe_version_components_versions_value_object_should_raise_if_invalid_components_versions(
    components_versions,
    expected_exception_message,
):
    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_components_versions_value_object.from_list(components_versions)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_version_description_value_object_should_parse_description():
    # ARRANGE
    description = "-This_is_a_valid_description-"

    # ACT
    value_object = recipe_version_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(description)


def test_recipe_version_description_value_object_should_raise_if_invalid_characters():
    # ARRANGE
    description = "This is an invalid description..."
    expected_exception_message = "Recipe version description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_version_description_value_object_should_raise_if_empty_string():
    # ARRANGE
    description = " "
    expected_exception_message = "Recipe version description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_version_description_value_object_should_raise_if_too_long():
    # ARRANGE
    description = "This is an invalid description because it is very long and it is not the case to be this verbose or maybe it is"
    expected_exception_message = "Recipe version description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version.RecipeVersionReleaseType.list",
    mock.MagicMock(return_value=["TEST_RELEASE_1", "TEST_RELEASE_2"]),
)
def test_component_version_release_type_value_object_should_parse_release_type():
    # ARRANGE
    release_type = "TEST_RELEASE_1"

    # ACT
    value_object = recipe_version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(release_type)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version.RecipeVersionReleaseType.list",
    mock.MagicMock(return_value=["TEST_RELEASE_1", "TEST_RELEASE_2"]),
)
def test_component_version_release_type_value_object_should_raise_if_invalid_release_type():
    # ARRANGE
    release_type = "TEST_RELEASE_INVALID"
    expected_exception_message = "Recipe version release type should be in ['TEST_RELEASE_1', 'TEST_RELEASE_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version.RecipeVersionStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_component_version_status_value_object_should_parse_status():
    # ARRANGE
    status = "TEST_STATUS_1"

    # ACT
    value_object = recipe_version_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(status)


@mock.patch(
    "app.packaging.domain.model.recipe.recipe_version.RecipeVersionStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_component_version_status_value_object_should_raise_if_invalid_status():
    # ARRANGE
    status = "TEST_STATUS_INVALID"
    expected_exception_message = "Recipe version status should be in ['TEST_STATUS_1', 'TEST_STATUS_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_version_parent_image_upstream_id_value_object_should_parse_image_id():
    # ARRANGE
    image_id = "ami-1234567890abcdefg"

    # ACT
    value_object = recipe_version_parent_image_upstream_id_value_object.from_str(image_id)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(image_id)


def test_component_version_test_execution_image_upstream_id_value_object_should_raise_if_invalid_image_id():
    # ARRANGE
    image_id = "ami-abcdef-12345"
    expected_exception_message = "Parent image upstream id should match ami-[a-z|0-9]{0,17} pattern."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_parent_image_upstream_id_value_object.from_str(image_id)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_version_arn_value_object_should_parse_arn():
    # ARRANGE
    arn = "arn:aws:imagebuilder:us-east-1:123456789123:image-recipe/reci_00000000/1.0.0"

    # ACT
    value_object = recipe_version_arn_value_object.from_str(arn)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(arn)


def test_recipe_version_arn_value_object_should_raise_if_invalid_arn():
    # ARRANGE
    arn = "arn:aws:imagebuilder:us-east-1:123456789123:imagerecipe/reci_00000000/1.0.0"
    expected_exception_message = "Recipe version ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):image-recipe/[a-z0-9-_]+/[0-9]+\\.[0-9]+\\.[0-9]+$ pattern."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_version_arn_value_object.from_str(arn)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_component_version_entry_should_raise_exception_when_wrong_component_type():
    # ARRANGE & ACT
    with pytest.raises(ValueError) as exec_info:
        component_version_entry.ComponentVersionEntry(
            componentId="XXXXXXXXXXXX",
            componentName="component-1234pqr",
            componentVersionId="XXXXXXXXXXXX",
            componentVersionName="3.0.0",
            componentVersionType="dummy_value",
            order=1,
        )
    # ASSERT
    assertpy.assert_that(str(exec_info.value)).contains("1 validation error for ComponentVersionEntry")


@pytest.mark.parametrize(
    "recipe_version_volume_size,expected_exception_message",
    (
        (None, "Recipe version volume size cannot be empty."),
        ("", "Recipe version volume size cannot be empty."),
        ("7", "Recipe version volume size must be included between 8 and 500 GB."),
        ("501", "Recipe version volume size must be included between 8 and 500 GB."),
        ("A", "Recipe version volume size must be a valid integer."),
    ),
)
def test_recipe_version_volume_size_value_object_should_raise_if_invalid_volume_size(
    recipe_version_volume_size, expected_exception_message
):
    # ARRANGE & ACT
    with pytest.raises(DomainException) as e:
        recipe_version_volume_size_value_object.from_str(recipe_version_volume_size)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)
