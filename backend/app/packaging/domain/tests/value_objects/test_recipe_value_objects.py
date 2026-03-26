import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.value_objects.recipe import (
    recipe_component_version_arn_value_object,
    recipe_description_value_object,
)


def test_recipe_component_version_arn_value_object_should_parse_arns():
    # ARRANGE
    arns = [
        "arn:aws:imagebuilder:us-east-1:123456789123:component/comp_00000000/1.0.0/1",
        "arn:aws:imagebuilder:us-east-1:123456789123:component/comp_00000001/1.0.0/1",
    ]

    # ACT
    value_object = recipe_component_version_arn_value_object.from_list(arns)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(arns)


def test_recipe_component_version_arn_value_object_should_raise_if_invalid_arn():
    # ARRANGE
    arns = ["arn:aws:imagebuilder:us-east-1:123456789123:component/comp_00000000/1.0.0"]
    expected_exception_message = "Component build version ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):component/[a-z0-9-_]+/[0-9]+\\.[0-9]+\\.[0-9]+/[0-9]+?$ pattern."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_component_version_arn_value_object.from_list(arns)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_description_value_object_should_parse_description():
    # ARRANGE
    description = "-This_is_a_valid_description-"

    # ACT
    value_object = recipe_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(description)


def test_recipe_description_value_object_should_raise_if_invalid_characters():
    # ARRANGE
    description = "This is an invalid description..."
    expected_exception_message = "Recipe description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_description_value_object_should_raise_if_empty_string():
    # ARRANGE
    description = " "
    expected_exception_message = "Recipe description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_recipe_description_value_object_should_raise_if_too_long():
    # ARRANGE
    description = "This is an invalid description because it is very long and it is not the case to be this verbose or maybe it is"
    expected_exception_message = "Recipe description should be between 0 and 100 characters in alphanumeric, space( ), underscore(_) and hyphen(-)."

    # ACT
    with pytest.raises(DomainException) as e:
        recipe_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)
