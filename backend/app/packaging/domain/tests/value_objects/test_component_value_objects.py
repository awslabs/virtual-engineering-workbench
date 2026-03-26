from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.value_objects.component import (
    component_build_version_arn_value_object,
    component_description_value_object,
    component_supported_architecture_value_object,
    component_supported_os_version_value_object,
)


def test_component_build_version_arn_value_object_should_parse_arn():
    # ARRANGE
    arn = "arn:aws:imagebuilder:us-east-1:123456789123:component/comp_00000000/1.0.0/1"

    # ACT
    value_object = component_build_version_arn_value_object.from_str(arn)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(arn)


def test_component_build_version_arn_value_object_should_raise_if_invalid_arn():
    # ARRANGE
    arn = "arn:aws:imagebuilder:us-east-1:123456789123:component/comp_00000000/1.0.0"
    expected_exception_message = "Component build version ARN should match ^arn:aws[^:]*:imagebuilder:[^:]+:(?:[0-9]{12}|aws):component/[a-z0-9-_]+/[0-9]+\\.[0-9]+\\.[0-9]+/[0-9]+$ pattern."

    # ACT
    with pytest.raises(DomainException) as e:
        component_build_version_arn_value_object.from_str(arn)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_component_description_value_object_should_parse_description():
    # ARRANGE
    description = "-This_is_a_valid_description-"

    # ACT
    value_object = component_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(description)


def test_component_description_value_object_should_raise_if_too_long():
    # ARRANGE
    description = ""
    for _ in range(16):
        description = description + "This is an invalid description as it is more than 1024 characters."
    expected_exception_message = "Component description should be between 0 and 1024 characters."

    # ACT
    with pytest.raises(DomainException) as e:
        component_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.component.component.ComponentSupportedArchitectures.list",
    mock.MagicMock(return_value=["TEST_ARCH_1", "TEST_ARCH_2"]),
)
def test_component_supported_architectures_value_object_should_parse_architecture():
    # ARRANGE
    arch = "TEST_ARCH_1"

    # ACT
    value_object = component_supported_architecture_value_object.from_str(arch)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(arch)


@mock.patch(
    "app.packaging.domain.model.component.component.ComponentSupportedArchitectures.list",
    mock.MagicMock(return_value=["TEST_ARCH_1", "TEST_ARCH_2"]),
)
def test_component_supported_architectures_value_object_should_raise_if_invalid_architecture():
    # ARRANGE
    arch = "TEST_ARCH_INVALID"
    expected_exception_message = "Component supported architecture should be in ['TEST_ARCH_1', 'TEST_ARCH_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        component_supported_architecture_value_object.from_str(arch)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.component.component.ComponentSupportedOsVersions.list",
    mock.MagicMock(return_value=["TEST_OS_1", "TEST_OS_2"]),
)
def test_component_supported_os_version_value_object_should_parse_os():
    # ARRANGE
    os = "TEST_OS_1"

    # ACT
    value_object = component_supported_os_version_value_object.from_str(os)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(os)


@mock.patch(
    "app.packaging.domain.model.component.component.ComponentSupportedOsVersions.list",
    mock.MagicMock(return_value=["TEST_OS_1", "TEST_OS_2"]),
)
def test_component_supported_os_version_value_object_should_raise_if_invalid_os():
    # ARRANGE
    os = "TEST_OS_INVALID"
    expected_exception_message = "Component supported OS version should be in ['TEST_OS_1', 'TEST_OS_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        component_supported_os_version_value_object.from_str(os)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)
