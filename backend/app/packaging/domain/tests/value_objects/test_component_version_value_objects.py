from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.packaging.domain.value_objects.component_version import (
    component_license_dashboard_url_value_object,
    component_software_vendor_value_object,
    component_software_version_value_object,
    component_version_dependencies_value_object,
    component_version_description_value_object,
    component_version_release_type_value_object,
    component_version_status_value_object,
)


def test_component_version_dependencies_value_object_should_parse_dependencies():
    # ARRANGE
    dependencies = [
        ComponentVersionEntry(
            componentId="comp-00000000",
            componentName="test-component-00000000",
            componentVersionId="vers-00000000",
            componentVersionName="1.0.0",
            order=1,
        ),
        ComponentVersionEntry(
            componentId="comp-00000001",
            componentName="test-component-00000001",
            componentVersionId="vers-00000001",
            componentVersionName="1.0.0",
            order=2,
        ),
    ]

    # ACT
    value_object = component_version_dependencies_value_object.from_list(dependencies)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(dependencies)


@pytest.mark.parametrize(
    "dependencies,expected_exception_message",
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
def test_component_version_dependencies_value_object_should_raise_if_invalid_dependencies(
    dependencies,
    expected_exception_message,
):
    # ACT
    with pytest.raises(DomainException) as e:
        component_version_dependencies_value_object.from_list(dependencies)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


def test_component_version_description_value_object_should_parse_description():
    # ARRANGE
    description = "-This_is_a_valid_description-"

    # ACT
    value_object = component_version_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(description)


def test_component_version_description_value_object_should_raise_if_too_long():
    # ARRANGE
    description = ""
    for _ in range(16):
        description = description + "This is an invalid description as it is more than 1024 characters."
    expected_exception_message = "Component version description should be between 0 and 1024 characters."

    # ACT
    with pytest.raises(DomainException) as e:
        component_version_description_value_object.from_str(description)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.component.component_version.ComponentVersionReleaseType.list",
    mock.MagicMock(return_value=["TEST_RELEASE_1", "TEST_RELEASE_2"]),
)
def test_component_version_release_type_value_object_should_parse_release_type():
    # ARRANGE
    release_type = "TEST_RELEASE_1"

    # ACT
    value_object = component_version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(release_type)


@mock.patch(
    "app.packaging.domain.model.component.component_version.ComponentVersionReleaseType.list",
    mock.MagicMock(return_value=["TEST_RELEASE_1", "TEST_RELEASE_2"]),
)
def test_component_version_release_type_value_object_should_raise_if_invalid_release_type():
    # ARRANGE
    release_type = "TEST_RELEASE_INVALID"
    expected_exception_message = "Component version release type should be in ['TEST_RELEASE_1', 'TEST_RELEASE_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        component_version_release_type_value_object.from_str(release_type)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@mock.patch(
    "app.packaging.domain.model.component.component_version.ComponentVersionStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_component_version_status_value_object_should_parse_status():
    # ARRANGE
    status = "TEST_STATUS_1"

    # ACT
    value_object = component_version_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(value_object.value).is_equal_to(status)


@mock.patch(
    "app.packaging.domain.model.component.component_version.ComponentVersionStatus.list",
    mock.MagicMock(return_value=["TEST_STATUS_1", "TEST_STATUS_2"]),
)
def test_component_version_status_value_object_should_raise_if_invalid_status():
    # ARRANGE
    status = "TEST_STATUS_INVALID"
    expected_exception_message = "Component version status should be in ['TEST_STATUS_1', 'TEST_STATUS_2']."

    # ACT
    with pytest.raises(DomainException) as e:
        component_version_status_value_object.from_str(status)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)


@pytest.mark.parametrize(
    "license_dashboard_url, error_message",
    [
        (
            "htttps://proserve.license.com",
            "License dashboard link is not valid: htttps://proserve.license.com. The URL scheme must be 'http' or 'https'.",
        ),
        (
            "htttp://proserve.license.com",
            "License dashboard link is not valid: htttp://proserve.license.com. The URL scheme must be 'http' or 'https'.",
        ),
        (
            "https:///index.html",
            "License dashboard link is not valid: https:///index.html. The URL must contain a hostname.",
        ),
    ],
)
def test_component_license_dashboard_url_value_object_should_raise_domain_exception(
    license_dashboard_url, error_message
):
    # ACT
    with pytest.raises(DomainException) as e:
        component_license_dashboard_url_value_object.from_str(license_dashboard_url)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(error_message)


@pytest.mark.parametrize(
    "license_dashboard_url",
    [
        "https://proserve.vector-license.com",
        "https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1",
    ],
)
def test_component_license_dashboard_url_value_object_should_parse_license_dashboard_url(
    license_dashboard_url,
):
    # ACT
    license_dashboard = component_license_dashboard_url_value_object.from_str(license_dashboard_url)

    # ASSERT
    assertpy.assert_that(license_dashboard.value).is_equal_to(license_dashboard_url)


def test_software_vendor_value_object_should_parse_vendor_name():
    # ARRANGE
    vendor_name = "vector"

    # ACT
    vendor = component_software_vendor_value_object.from_str(vendor_name)

    # ASSERT
    assertpy.assert_that(vendor.value).is_equal_to(vendor_name)


def test_software_vendor_value_object_should_fail_if_not_passed():
    # ARRANGE
    vendor_name = None

    # ACT
    with pytest.raises(DomainException) as e:
        component_software_vendor_value_object.from_str(vendor_name)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Software vendor cannot be empty.")


def test_software_version_value_object_should_parse_version():
    # ARRANGE
    version = "1.0.0"

    # ACT
    vendor = component_software_version_value_object.from_str(version)

    # ASSERT
    assertpy.assert_that(vendor.value).is_equal_to(version)


def test_software_version_value_object_should_fail_if_not_passed():
    # ARRANGE
    version = None

    # ACT
    with pytest.raises(DomainException) as e:
        component_software_version_value_object.from_str(version)

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Software version cannot be empty.")


def test_component_version_entry_should_create_with_prepend_position():
    # ARRANGE & ACT
    entry = ComponentVersionEntry(
        componentId="comp-123",
        componentName="TestComponent",
        componentVersionId="vers-456",
        componentVersionName="1.0.0",
        order=1,
        position="PREPEND",
    )

    # ASSERT
    assertpy.assert_that(entry.componentId).is_equal_to("comp-123")
    assertpy.assert_that(entry.position).is_equal_to("PREPEND")
    assertpy.assert_that(entry.order).is_equal_to(1)


def test_component_version_entry_should_create_with_append_position():
    # ARRANGE & ACT
    entry = ComponentVersionEntry(
        componentId="comp-789",
        componentName="AnotherComponent",
        componentVersionId="vers-012",
        componentVersionName="2.0.0",
        order=2,
        position="APPEND",
    )

    # ASSERT
    assertpy.assert_that(entry.componentId).is_equal_to("comp-789")
    assertpy.assert_that(entry.position).is_equal_to("APPEND")
    assertpy.assert_that(entry.order).is_equal_to(2)


def test_component_version_entry_should_have_none_position_by_default():
    # ARRANGE & ACT
    entry = ComponentVersionEntry(
        componentId="comp-999",
        componentName="UserComponent",
        componentVersionId="vers-888",
        componentVersionName="3.0.0",
        order=3,
    )

    # ASSERT
    assertpy.assert_that(entry.position).is_none()
    assertpy.assert_that(entry.order).is_equal_to(3)


def test_mandatory_components_versions_value_object_should_preserve_position_field():
    # ARRANGE
    from app.packaging.domain.value_objects.component_version import (
        mandatory_components_versions_value_object,
    )

    components = [
        ComponentVersionEntry(
            componentId="comp-1",
            componentName="Component1",
            componentVersionId="vers-1",
            componentVersionName="1.0.0",
            order=1,
            position="PREPEND",
        ),
        ComponentVersionEntry(
            componentId="comp-2",
            componentName="Component2",
            componentVersionId="vers-2",
            componentVersionName="2.0.0",
            order=2,
            position="APPEND",
        ),
    ]

    # ACT
    value_object = mandatory_components_versions_value_object.from_list(components)

    # ASSERT
    assertpy.assert_that(value_object.value).is_length(2)
    assertpy.assert_that(value_object.value[0].position).is_equal_to("PREPEND")
    assertpy.assert_that(value_object.value[1].position).is_equal_to("APPEND")


@pytest.mark.parametrize(
    "components,expected_exception_message",
    (
        (
            [
                ComponentVersionEntry(
                    componentId="",
                    componentName="Component",
                    componentVersionId="vers-1",
                    componentVersionName="1.0.0",
                    order=1,
                ),
            ],
            "Component ID cannot be empty.",
        ),
        (
            [
                ComponentVersionEntry(
                    componentId="comp-1",
                    componentName="Component",
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
                    componentId="comp-1",
                    componentName="Component",
                    componentVersionId="vers-1",
                    componentVersionName="1.0.0",
                    order=None,
                ),
            ],
            "Order cannot be empty.",
        ),
    ),
)
def test_mandatory_components_versions_value_object_should_raise_if_invalid(
    components,
    expected_exception_message,
):
    # ARRANGE
    from app.packaging.domain.value_objects.component_version import (
        mandatory_components_versions_value_object,
    )

    # ACT & ASSERT
    with pytest.raises(DomainException) as e:
        mandatory_components_versions_value_object.from_list(components)

    assertpy.assert_that(str(e.value)).is_equal_to(expected_exception_message)
