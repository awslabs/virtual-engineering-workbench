from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component.create_component_command_handler import (
    handle,
)
from app.packaging.domain.commands.component.create_component_command import (
    CreateComponentCommand,
)
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.component import component
from app.packaging.domain.model.component.component_project_association import (
    ComponentProjectAssociation,
)
from app.packaging.domain.value_objects.component import (
    component_description_value_object,
    component_id_value_object,
    component_name_value_object,
    component_system_configuration_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
)


@freeze_time("2023-10-13T00:00:00+00:00")
def create_component_command_component_platform_fail_mock() -> CreateComponentCommand:
    return CreateComponentCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        componentId=component_id_value_object.from_str("comp-12345abc"),
        componentName=component_name_value_object.from_str("proserve-autosar-component"),
        componentDescription=component_description_value_object.from_str("This is a component for validation"),
        componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
            platform="LINUX",
            supported_architectures=["amd64"],
            supported_os_versions=["Ubuntu 24"],
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_component_command_supported_architectures_fail_mock() -> CreateComponentCommand:
    return CreateComponentCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        componentName=component_name_value_object.from_str("proserve-autosar-component"),
        componentDescription=component_description_value_object.from_str("This is a component for validation"),
        componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
            platform="Linux",
            supported_architectures=["RISC-V"],
            supported_os_versions=["Ubuntu 24"],
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_component_command_component_supported_os_versions_fail_mock() -> CreateComponentCommand:
    return CreateComponentCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        componentId=component_id_value_object.from_str("comp-12345abc"),
        componentName=component_name_value_object.from_str("proserve-autosar-component"),
        componentDescription=component_description_value_object.from_str("This is a component for validation"),
        componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
            platform="Linux",
            supported_architectures=["amd64"],
            supported_os_versions=["Ubuntu 26"],
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_component_command_component_incompatible_platform_architectures_fail_mock() -> CreateComponentCommand:
    return CreateComponentCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        componentId=component_id_value_object.from_str("comp-12345abc"),
        componentName=component_name_value_object.from_str("proserve-autosar-component"),
        componentDescription=component_description_value_object.from_str("This is a component for validation"),
        componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
            platform="Windows",
            supported_architectures=["arm64"],
            supported_os_versions=["Microsoft Windows Server 2025"],
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def create_component_command_component_incompatible_platform_os_versions_fail_mock() -> CreateComponentCommand:
    return CreateComponentCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        componentId=component_id_value_object.from_str("comp-12345abc"),
        componentName=component_name_value_object.from_str("proserve-autosar-component"),
        componentDescription=component_description_value_object.from_str("This is a component for validation"),
        componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
            platform="Windows",
            supported_architectures=["amd64"],
            supported_os_versions=["Ubuntu 24"],
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


def test_create_command_component_should_raise_exception_with_invalid_platform():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_component_command_component_platform_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Component platform should be in {component.ComponentPlatform.list()}."
    )


def test_create_command_component_should_raise_exception_with_invalid_supported_architectures():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_component_command_supported_architectures_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Component supported architecture should be in {component.ComponentSupportedArchitectures.list()}."
    )


def test_create_command_component_should_raise_exception_with_invalid_supported_os_versions():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_component_command_component_supported_os_versions_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        f"Component supported OS version should be in {component.ComponentSupportedOsVersions.list()}."
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def test_create_component_should_raise_exception_with_incompatible_platform_architectures():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_component_command_component_incompatible_platform_architectures_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Component platform Windows does not support arm64 architecture."
    )


@freeze_time("2023-10-13T00:00:00+00:00")
def test_create_component_should_raise_exception_with_incompatible_platform_os_versions():
    # ARRANGE & ACT
    with pytest.raises(DomainException) as exec_info:
        create_component_command_component_incompatible_platform_os_versions_fail_mock()

    # ASSERT
    assertpy.assert_that(str(exec_info.value)).is_equal_to(
        "Component platform Windows does not support Linux OS versions."
    )


@pytest.fixture()
@freeze_time("2023-10-13T00:00:00+00:00")
def create_component_command_mock() -> CreateComponentCommand:
    return CreateComponentCommand(
        projectId=project_id_value_object.from_str("proj-12345"),
        componentId=component_id_value_object.from_str("comp-11111111"),
        componentName=component_name_value_object.from_str("proserve-autosar-component"),
        componentDescription=component_description_value_object.from_str("This is a component for validation"),
        componentSystemConfiguration=component_system_configuration_value_object.from_attrs(
            platform="Linux",
            supported_architectures=["amd64"],
            supported_os_versions=["Ubuntu 24"],
        ),
        createdBy=user_id_value_object.from_str("T998765"),
        createDate="2023-10-13T00:00:00+00:00",
    )


@pytest.fixture()
def mock_component_object() -> component.Component:
    return component.Component(
        componentId="comp-11111111",
        componentName="proserve-autosar-component",
        componentDescription="This is a component for validation",
        componentPlatform="Linux",
        componentSupportedArchitectures=["amd64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        status=component.ComponentStatus.Created,
        createdBy="T998765",
        createDate="2023-10-13T00:00:00+00:00",
        lastUpdatedBy="T998765",
        lastUpdateDate="2023-10-13T00:00:00+00:00",
    )


@pytest.fixture()
def mock_project_component_association_object(
    mock_component_object,
) -> ComponentProjectAssociation:
    return ComponentProjectAssociation(
        componentId=mock_component_object.componentId,
        projectId="proj-12345",
    )


@mock.patch(
    "app.packaging.domain.value_objects.component.component_id_value_object.random.choice",
    lambda chars: "1",
)
@freeze_time("2023-10-13T00:00:00+00:00")
def test_create_component_should_create_new_component(
    create_component_command_mock,
    mock_component_object,
    mock_project_component_association_object,
    generic_repo_mock,
    uow_mock,
):
    # ARRANGE & ACT
    handle(create_component_command_mock, uow=uow_mock)

    # ASSERT
    generic_repo_mock.add.assert_has_calls(
        [
            mock.call(mock_component_object),
            mock.call(mock_project_component_association_object),
        ]
    )
    uow_mock.commit.assert_called()
