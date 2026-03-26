from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    create_component_version_command_handler,
)
from app.packaging.domain.commands.component import create_component_version_command
from app.packaging.domain.events.component import component_version_creation_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component, component_version
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_license_dashboard_url_value_object,
    component_software_vendor_value_object,
    component_software_version_notes_value_object,
    component_software_version_value_object,
    component_version_dependencies_value_object,
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_name_value_object,
    component_version_release_type_value_object,
    component_version_yaml_definition_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def create_component_version_command_mock():
    def _create_component_version_command_mock(
        get_test_component_yaml_definition,
        license_dashboard="https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1",
        notes="This component is a test component",
        software_vendor="vector",
        software_version="1.0.0",
    ) -> create_component_version_command.CreateComponentVersionCommand:
        return create_component_version_command.CreateComponentVersionCommand(
            componentId=component_id_value_object.from_str("comp-1234abcd"),
            componentVersionDescription=component_version_description_value_object.from_str("Test description"),
            componentVersionReleaseType=component_version_release_type_value_object.from_str("MAJOR"),
            componentVersionDependencies=component_version_dependencies_value_object.from_list([]),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
                get_test_component_yaml_definition()
            ),
            softwareVendor=component_software_vendor_value_object.from_str(software_vendor),
            softwareVersion=component_software_version_value_object.from_str(software_version),
            licenseDashboard=component_license_dashboard_url_value_object.from_str(license_dashboard),
            notes=component_software_version_notes_value_object.from_str(notes),
            createdBy=user_id_value_object.from_str("T123456"),
        )

    return _create_component_version_command_mock


@pytest.mark.parametrize(
    "fetched_release_name,release_type,expected_version_name",
    (
        (
            "2.0.0",
            component_version.ComponentVersionReleaseType.Major.value,
            "3.0.0-rc.1",
        ),
        (
            "2.0.100",
            component_version.ComponentVersionReleaseType.Major.value,
            "3.0.0-rc.1",
        ),
        (
            "1.2.0",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
        (
            "1.2.100",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
        (
            "2.5.10",
            component_version.ComponentVersionReleaseType.Patch.value,
            "2.5.11-rc.1",
        ),
    ),
)
@mock.patch(
    "app.packaging.domain.model.component.component_version.random.choice",
    lambda chars: "1",
)
@freeze_time("2023-09-29")
def test_handle_should_create_new_version_if_version_in_repository(
    fetched_release_name,
    release_type,
    expected_version_name,
    create_component_version_command_mock,
    component_query_service_mock,
    component_version_query_service_mock,
    get_test_component,
    get_test_component_yaml_definition,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_query_service_mock.get_component.return_value = get_test_component
    component_version_query_service_mock.get_latest_component_version_name.return_value = fetched_release_name
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    command = create_component_version_command_mock(get_test_component_yaml_definition)
    command.componentVersionReleaseType = component_version_release_type_value_object.from_str(release_type)

    # ACT
    create_component_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_qry_srv=component_query_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    component_version_repo_mock.add.assert_called_once_with(
        component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-11111111",
            componentVersionName=expected_version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentPlatform="Linux",
            componentSupportedArchitectures=["amd64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            componentVersionDependencies=[],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            licenseDashboard="https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1",
            notes="This component is a test component",
            status=component_version.ComponentVersionStatus.Creating,
            createDate="2023-09-29T00:00:00+00:00",
            createdBy="T123456",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            lastUpdatedBy="T123456",
        )
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_creation_started.ComponentVersionCreationStarted(
            component_id="comp-1234abcd",
            component_version_id="vers-11111111",
            component_version_description="Test description",
            component_version_name=expected_version_name,
            component_version_yaml_definition=get_test_component_yaml_definition(),
            component_version_dependencies=list(),
        )
    )


@pytest.mark.parametrize(
    "fetched_release_name,release_type,expected_version_name",
    (
        (None, component_version.ComponentVersionReleaseType.Major.value, "1.0.0-rc.1"),
        (None, component_version.ComponentVersionReleaseType.Minor.value, "1.0.0-rc.1"),
        (None, component_version.ComponentVersionReleaseType.Patch.value, "1.0.0-rc.1"),
    ),
)
@mock.patch(
    "app.packaging.domain.model.component.component_version.random.choice",
    lambda chars: "1",
)
@freeze_time("2023-09-29")
def test_handle_should_create_new_initial_version_if_no_version_in_repository(
    fetched_release_name,
    release_type,
    expected_version_name,
    create_component_version_command_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    get_test_component,
    get_test_component_yaml_definition,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_query_service_mock.get_component.return_value = get_test_component
    component_version_query_service_mock.get_latest_component_version_name.return_value = fetched_release_name
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    command = create_component_version_command_mock(get_test_component_yaml_definition)
    command.componentVersionReleaseType = component_version_release_type_value_object.from_str(release_type)

    # ACT
    create_component_version_command_handler.handle(
        command=command,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
        component_qry_srv=component_query_service_mock,
    )

    # ASSERT
    component_version_repo_mock.add.assert_called_once_with(
        component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-11111111",
            componentVersionName=expected_version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentPlatform="Linux",
            componentSupportedArchitectures=["amd64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            componentVersionDependencies=[],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            licenseDashboard="https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1",
            notes="This component is a test component",
            status=component_version.ComponentVersionStatus.Creating,
            createDate="2023-09-29T00:00:00+00:00",
            createdBy="T123456",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            lastUpdatedBy="T123456",
        )
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_creation_started.ComponentVersionCreationStarted(
            component_id="comp-1234abcd",
            component_version_id="vers-11111111",
            component_version_description="Test description",
            component_version_name=expected_version_name,
            component_version_yaml_definition=get_test_component_yaml_definition(),
            component_version_dependencies=list(),
        )
    )


def test_create_should_raise_if_component_not_found(
    create_component_version_command_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    get_test_component_yaml_definition,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_query_service_mock.get_component.return_value = None
    component_version_query_service_mock.get_latest_component_version_name.return_value = "1.0.0-rc.1"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    command = create_component_version_command_mock(get_test_component_yaml_definition)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        create_component_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            component_qry_srv=component_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Component comp-1234abcd can not be found.")


def test_create_should_raise_if_component_status_is_archived(
    create_component_version_command_mock,
    component_version_query_service_mock,
    component_query_service_mock,
    get_test_component,
    get_test_component_yaml_definition,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    test_component = get_test_component
    test_component.status = component.ComponentStatus.Archived
    component_query_service_mock.get_component.return_value = test_component
    component_version_query_service_mock.get_latest_component_version_name.return_value = "1.0.0-rc.1"
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    command = create_component_version_command_mock(get_test_component_yaml_definition)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        create_component_version_command_handler.handle(
            command=command,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
            component_qry_srv=component_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Component comp-1234abcd is in ARCHIVED status.")


def test_handle_should_raise_exception_when_component_yaml_is_invalid():
    # ARRANGE & ACT & ASSERT
    with pytest.raises(domain_exception.DomainException) as e:
        create_component_version_command.CreateComponentVersionCommand(
            componentId=component_id_value_object.from_str("comp-1234abcd"),
            componentVersionId=component_version_id_value_object.from_str("vers-11111111"),
            componentVersionName=component_version_name_value_object.from_str("1.0.0-rc.1"),
            componentVersionDescription=component_version_description_value_object.from_str("Test description"),
            componentVersionReleaseType=component_version_release_type_value_object.from_str("MAJOR"),
            componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str("Invalid YAML"),
        )
    assertpy.assert_that(str(e.value)).is_equal_to("Component version YAML definition is invalid.")


@pytest.fixture()
def create_component_version_with_dependencies_command_mock(
    get_test_component_yaml_definition,
) -> create_component_version_command.CreateComponentVersionCommand:
    return create_component_version_command.CreateComponentVersionCommand(
        componentId=component_id_value_object.from_str("comp-1234abcd"),
        componentVersionDescription=component_version_description_value_object.from_str("Test description"),
        componentVersionReleaseType=component_version_release_type_value_object.from_str("MAJOR"),
        componentVersionDependencies=component_version_dependencies_value_object.from_list(
            [
                ComponentVersionEntry(
                    componentId="comp-8675abc",
                    componentName="component-8675abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="2.0.0-rc1",
                    order=2,
                ),
                ComponentVersionEntry(
                    componentId="comp2-1234abc",
                    componentName="component2-1234abc",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                ComponentVersionEntry(
                    componentId="comp3-9867dfg",
                    componentName="component3-9867dfg",
                    componentVersionId="vers-1234abcd",
                    componentVersionName="3.0.0",
                    order=3,
                ),
            ]
        ),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            get_test_component_yaml_definition()
        ),
        softwareVendor=component_software_vendor_value_object.from_str("vector"),
        softwareVersion=component_software_version_value_object.from_str("1.0.2"),
        createdBy=user_id_value_object.from_str("T123456"),
    )


@pytest.fixture()
def return_component_version_for_component_dependecies():
    def _return_dependency_component_version(
        componentId: str,
        componentVersionId: str,
        componentVersionName: str,
        componentName: str,
        status: str,
    ):
        if componentId is None:
            return None
        return component_version.ComponentVersion(
            componentId=componentId,
            componentName=componentName,
            componentVersionId=componentVersionId,
            componentVersionName=componentVersionName,
            componentVersionDescription="test component order",
            componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/{componentId}/{componentVersionName}/1",
            componentVersionS3Uri=f"s3://test-component-bucket/{componentId}/{componentVersionName}/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["amd64", "arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            softwareVendor="vector",
            softwareVersion="1.0.2",
            licenseDashboard="https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1",
            notes="This component is a test component.",
            status=status,
            createDate="2024-01-11",
            createdBy="2024-01-11",
            lastUpdateDate="2024-01-11",
            lastUpdatedBy="T0000001",
        )

    return _return_dependency_component_version


@pytest.mark.parametrize(
    "status,fetched_release_name,release_type,expected_version_name",
    (
        (
            component_version.ComponentVersionStatus.Validated.value,
            "2.0.0",
            component_version.ComponentVersionReleaseType.Major.value,
            "3.0.0-rc.1",
        ),
        (
            component_version.ComponentVersionStatus.Released.value,
            "1.2.0",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
    ),
)
@mock.patch(
    "app.packaging.domain.model.component.component_version.random.choice",
    lambda chars: "1",
)
@freeze_time("2023-09-29")
def test_create_component_version_command_handler_should_create_a_component_when_valid_dependency_in_valid_status(
    status,
    fetched_release_name,
    release_type,
    expected_version_name,
    create_component_version_with_dependencies_command_mock,
    component_query_service_mock,
    component_version_query_service_mock,
    get_test_component,
    get_test_component_yaml_definition,
    return_component_version_for_component_dependecies,
    uow_mock,
    message_bus_mock,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version_for_component_dependecies(
            componentId=item.componentId,
            componentVersionId=item.componentVersionId,
            componentVersionName=item.componentVersionName,
            componentName=item.componentName,
            status=status,
        )
        for item in create_component_version_with_dependencies_command_mock.componentVersionDependencies.value
    ]
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_query_service_mock.get_component.return_value = get_test_component
    component_version_query_service_mock.get_latest_component_version_name.return_value = fetched_release_name
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_component_version_with_dependencies_command_mock.componentVersionReleaseType = (
        component_version_release_type_value_object.from_str(release_type)
    )

    component_version_dependencies = [
        ComponentVersionEntry(
            componentId="comp-8675abc",
            componentName="component-8675abc",
            componentVersionId="vers-1234abcd",
            componentVersionName="2.0.0-rc1",
            order=2,
        ),
        ComponentVersionEntry(
            componentId="comp2-1234abc",
            componentName="component2-1234abc",
            componentVersionId="vers-1234abcd",
            componentVersionName="1.0.0",
            order=1,
        ),
        ComponentVersionEntry(
            componentId="comp3-9867dfg",
            componentName="component3-9867dfg",
            componentVersionId="vers-1234abcd",
            componentVersionName="3.0.0",
            order=3,
        ),
    ]

    # ACT
    create_component_version_command_handler.handle(
        command=create_component_version_with_dependencies_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_qry_srv=component_query_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    component_version_repo_mock.add.assert_called_once_with(
        component_version.ComponentVersion(
            componentId="comp-1234abcd",
            componentVersionId="vers-11111111",
            componentVersionName=expected_version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentPlatform="Linux",
            componentSupportedArchitectures=["amd64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            componentVersionDependencies=component_version_dependencies,
            softwareVendor="vector",
            softwareVersion="1.0.2",
            status=component_version.ComponentVersionStatus.Creating,
            createDate="2023-09-29T00:00:00+00:00",
            createdBy="T123456",
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            lastUpdatedBy="T123456",
        )
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_creation_started.ComponentVersionCreationStarted(
            component_id="comp-1234abcd",
            component_version_id="vers-11111111",
            component_version_description="Test description",
            component_version_name=expected_version_name,
            component_version_yaml_definition=get_test_component_yaml_definition(),
            component_version_dependencies=component_version_dependencies,
        )
    )


@pytest.mark.parametrize(
    "status,fetched_release_name,release_type,expected_version_name",
    (
        (
            component_version.ComponentVersionStatus.Validated.value,
            "2.0.0",
            component_version.ComponentVersionReleaseType.Major.value,
            "3.0.0-rc.1",
        ),
        (
            component_version.ComponentVersionStatus.Released.value,
            "1.2.0",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
    ),
)
@mock.patch(
    "app.packaging.domain.model.component.component_version.random.choice",
    lambda chars: "1",
)
@freeze_time("2023-09-29")
def test_create_component_version_command_handler_should_fail_when_dependent_component_version_not_found(
    status,
    fetched_release_name,
    release_type,
    expected_version_name,
    create_component_version_with_dependencies_command_mock,
    component_query_service_mock,
    component_version_query_service_mock,
    get_test_component,
    return_component_version_for_component_dependecies,
    uow_mock,
    message_bus_mock,
):
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version_for_component_dependecies(
            componentId=None,
            componentVersionId=item.componentVersionId,
            componentVersionName=item.componentVersionName,
            componentName=item.componentName,
            status=status,
        )
        for item in create_component_version_with_dependencies_command_mock.componentVersionDependencies.value
    ]
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_query_service_mock.get_component.return_value = get_test_component
    component_version_query_service_mock.get_latest_component_version_name.return_value = fetched_release_name
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_component_version_with_dependencies_command_mock.componentVersionReleaseType = (
        component_version_release_type_value_object.from_str(release_type)
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        create_component_version_command_handler.handle(
            command=create_component_version_with_dependencies_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_qry_srv=component_query_service_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Component comp-8675abc/component-8675abc not found.")


@pytest.mark.parametrize(
    "status,fetched_release_name,release_type,expected_version_name",
    (
        (
            component_version.ComponentVersionStatus.Creating.value,
            "2.0.0",
            component_version.ComponentVersionReleaseType.Major.value,
            "3.0.0-rc.1",
        ),
        (
            component_version.ComponentVersionStatus.Created.value,
            "1.2.0",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
        (
            component_version.ComponentVersionStatus.Failed.value,
            "1.2.0",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
        (
            component_version.ComponentVersionStatus.Retired.value,
            "1.2.0",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
        (
            component_version.ComponentVersionStatus.Updating.value,
            "1.2.0",
            component_version.ComponentVersionReleaseType.Minor.value,
            "1.3.0-rc.1",
        ),
    ),
)
@mock.patch(
    "app.packaging.domain.model.component.component_version.random.choice",
    lambda chars: "1",
)
@freeze_time("2023-09-29")
def test_create_component_version_command_handler_should_fail_when_dependent_component_version_not_in_valid_status(
    status,
    fetched_release_name,
    release_type,
    expected_version_name,
    create_component_version_with_dependencies_command_mock,
    component_query_service_mock,
    component_version_query_service_mock,
    get_test_component,
    return_component_version_for_component_dependecies,
    uow_mock,
    message_bus_mock,
):
    component_version_query_service_mock.get_component_version.side_effect = [
        return_component_version_for_component_dependecies(
            componentId=item.componentId,
            componentVersionId=item.componentVersionId,
            componentVersionName=item.componentVersionName,
            componentName=item.componentName,
            status=status,
        )
        for item in create_component_version_with_dependencies_command_mock.componentVersionDependencies.value
    ]
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_query_service_mock.get_component.return_value = get_test_component
    component_version_query_service_mock.get_latest_component_version_name.return_value = fetched_release_name
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    create_component_version_with_dependencies_command_mock.componentVersionReleaseType = (
        component_version_release_type_value_object.from_str(release_type)
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        create_component_version_command_handler.handle(
            command=create_component_version_with_dependencies_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_qry_srv=component_query_service_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Component comp-8675abc/component-8675abc not in a valid status: {status}."
    )
