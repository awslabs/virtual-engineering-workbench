from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    update_component_version_command_handler,
)
from app.packaging.domain.commands.component import update_component_version_command
from app.packaging.domain.events.component import component_version_update_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.packaging.domain.tests.conftest import (
    TEST_COMPONENT_ID,
    TEST_COMPONENT_NAME,
    TEST_COMPONENT_VERSION_ID,
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
    component_version_yaml_definition_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def update_component_version_command_mock(
    get_test_component_yaml_definition,
) -> update_component_version_command.UpdateComponentVersionCommand:
    return update_component_version_command.UpdateComponentVersionCommand(
        componentId=component_id_value_object.from_str("comp-1234abcd"),
        componentVersionId=component_version_id_value_object.from_str("vers-1234abcd"),
        componentVersionDescription=component_version_description_value_object.from_str("Test description"),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            get_test_component_yaml_definition()
        ),
        componentVersionDependencies=component_version_dependencies_value_object.from_list(list()),
        softwareVendor=component_software_vendor_value_object.from_str("Vector"),
        softwareVersion=component_software_version_value_object.from_str("1.0.2"),
        licenseDashboard=component_license_dashboard_url_value_object.from_str(
            "https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1"
        ),
        notes=component_software_version_notes_value_object.from_str("This component is a test component."),
        lastUpdatedBy=user_id_value_object.from_str("T000001"),
    )


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name",
    (
        ("2.0.0-rc.1", "2.0.0-rc.2"),
        ("2.1.0-rc.1", "2.1.0-rc.2"),
        ("2.0.1-rc.1", "2.0.1-rc.2"),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_update_version(
    fetched_release_name,
    expected_version_name,
    update_component_version_command_mock,
    component_version_query_service_mock,
    get_test_component_yaml_definition,
    get_test_component_version_with_specific_version_name_and_status,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_version_entity = get_test_component_version_with_specific_version_name_and_status(
        version_name=fetched_release_name,
        status=component_version.ComponentVersionStatus.Validated,
    )

    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    update_component_version_command_handler.handle(
        command=update_component_version_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    component_version_entity.lastUpdatedBy = update_component_version_command_mock.lastUpdatedBy.value
    component_version_entity.lastUpdateDate = "2023-10-12T00:00:00+00:00"
    component_version_entity.componentVersionDependencies = (
        update_component_version_command_mock.componentVersionDependencies.value
    )
    component_version_entity.componentVersionName = expected_version_name
    component_version_entity.componentVersionDescription = (
        update_component_version_command_mock.componentVersionDescription.value
    )
    component_version_entity.softwareVendor = update_component_version_command_mock.softwareVendor.value
    component_version_entity.softwareVersion = update_component_version_command_mock.softwareVersion.value
    component_version_entity.licenseDashboard = update_component_version_command_mock.licenseDashboard.value
    component_version_entity.notes = update_component_version_command_mock.notes.value
    component_version_entity.status = component_version.ComponentVersionStatus.Updating

    component_version_repo_mock.update_entity.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=update_component_version_command_mock.componentId.value,
            componentVersionId=update_component_version_command_mock.componentVersionId.value,
        ),
        component_version_entity,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_update_started.ComponentVersionUpdateStarted(
            component_id="comp-1234abcd",
            component_version_id="vers-1234abcd",
            component_version_description="Test description",
            component_version_name=expected_version_name,
            component_version_dependencies=[],
            component_version_yaml_definition=get_test_component_yaml_definition(),
            previous_component_version_dependencies=[
                ComponentVersionEntry(
                    componentId="comp-0",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=TEST_COMPONENT_VERSION_ID,
                    componentVersionName="1.0.2",
                    order=1,
                ),
                ComponentVersionEntry(
                    componentId="comp-1",
                    componentName=TEST_COMPONENT_NAME,
                    componentVersionId=f"{TEST_COMPONENT_VERSION_ID}",
                    componentVersionName="1.0.0",
                    order=2,
                ),
            ],
        )
    )


@pytest.mark.parametrize(
    "status",
    (
        component_version.ComponentVersionStatus.Created,
        component_version.ComponentVersionStatus.Creating,
        component_version.ComponentVersionStatus.Released,
        component_version.ComponentVersionStatus.Retired,
        component_version.ComponentVersionStatus.Testing,
        component_version.ComponentVersionStatus.Updating,
    ),
)
def test_update_component_version_command_handler_should_raise_an_exception_when_status_is_invalid(
    component_version_query_service_mock,
    get_test_component_version_with_specific_status,
    status,
    update_component_version_command_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_version_entity = get_test_component_version_with_specific_status(status=status)
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_command_handler.handle(
            command=update_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {component_version_entity.componentVersionName} of component "
        f"{component_version_entity.componentId} can't be updated while in {status} status."
    )


@pytest.mark.parametrize(
    "fetched_release_name",
    (
        ("2.0.0"),
        ("2.1.0"),
        ("2.0.1"),
    ),
)
def test_handle_should_raise_exception_when_version_is_not_rc(
    fetched_release_name,
    update_component_version_command_mock,
    component_version_query_service_mock,
    get_test_component_version_with_specific_version_name_and_status,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_version_query_service_mock.get_component_version.return_value = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name=fetched_release_name,
            status=component_version.ComponentVersionStatus.Validated,
        )
    )
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_command_handler.handle(
            command=update_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Can not update an already released component version ({fetched_release_name}) - only release candidates are allowed."
    )


def test_handle_should_raise_exception_when_component_version_is_none(
    update_component_version_command_mock,
    component_version_query_service_mock,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    component_version_query_service_mock.get_component_version.return_value = None
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda x: repos_dict.get(x)

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_command_handler.handle(
            command=update_component_version_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {update_component_version_command_mock.componentVersionId.value} of component "
        f"{update_component_version_command_mock.componentId.value} does not exist."
    )


@pytest.fixture()
def update_component_version_with_dependencies_command_mock(
    get_test_component_yaml_definition,
) -> update_component_version_command.UpdateComponentVersionCommand:
    return update_component_version_command.UpdateComponentVersionCommand(
        componentId=component_id_value_object.from_str("comp-1234abcd"),
        componentVersionId=component_version_id_value_object.from_str("vers-1234abcd"),
        componentVersionDescription=component_version_description_value_object.from_str("Test description"),
        componentVersionDependencies=component_version_dependencies_value_object.from_list(
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    order=3,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    order=2,
                ),
            ]
        ),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            get_test_component_yaml_definition()
        ),
        softwareVendor=component_software_vendor_value_object.from_str("vector"),
        softwareVersion=component_software_version_value_object.from_str("1.0.0"),
        lastUpdatedBy=user_id_value_object.from_str("T000001"),
    )


@pytest.fixture()
def return_dependent_component_version_for_update():
    def _return_lazy_component_version(
        componentName: str,
        componentId: str,
        componentVersionId: str,
        status: str,
        versionName: str = None,
    ):
        component_version_name = versionName if versionName is not None else "1.0.2"
        component_id = componentId
        component_version_id = componentVersionId
        if component_id is None:
            return None
        return component_version.ComponentVersion(
            componentId=component_id,
            componentName=componentName,
            componentVersionId=component_version_id,
            componentVersionName=component_version_name,
            componentVersionDescription="test component order",
            componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/{component_id}/{component_version_name}/1",
            componentVersionS3Uri=f"s3://test-component-bucket/{component_id}/{component_version_name}/component.yaml",
            componentPlatform="Linux",
            componentSupportedArchitectures=["amd64", "arm64"],
            componentSupportedOsVersions=["Ubuntu 24"],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            status=(component_version.ComponentVersionStatus.Validated if component_id == "comp-1234abcd" else status),
            createDate="2024-01-11",
            createdBy="2024-01-11",
            lastUpdateDate="2024-01-11",
            lastUpdatedBy="T0000001",
        )

    return _return_lazy_component_version


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name",
    (
        ("2.0.0-rc.1", "2.0.0-rc.2"),
        ("2.1.0-rc.1", "2.1.0-rc.2"),
        ("2.0.1-rc.1", "2.0.1-rc.2"),
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_succeed_when_dependent_components_are_present(
    fetched_release_name,
    expected_version_name,
    update_component_version_with_dependencies_command_mock,
    component_version_query_service_mock,
    get_test_component_yaml_definition,
    return_dependent_component_version_for_update,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    all_components = [
        {
            "componentId": update_component_version_with_dependencies_command_mock.componentId.value,
            "componentVersionId": update_component_version_with_dependencies_command_mock.componentVersionId.value,
            "componentName": "test-component",
            "status": component_version.ComponentVersionStatus.Validated.value,
            "versionName": fetched_release_name,
        }
    ]
    for dep in update_component_version_with_dependencies_command_mock.componentVersionDependencies.value:
        all_components.append(
            {
                "componentId": dep.componentId,
                "componentVersionId": dep.componentVersionId,
                "componentName": dep.componentName,
                "status": component_version.ComponentVersionStatus.Released,
            }
        )
    all_components_version_entities = [
        return_dependent_component_version_for_update(
            componentName=item.get("componentName"),
            componentId=item.get("componentId"),
            componentVersionId=item.get("componentVersionId"),
            status=item.get("status"),
            versionName=item.get("versionName", None),
        )
        for item in all_components
    ]
    component_version_entity_to_be_updated = all_components_version_entities[0]
    component_version_query_service_mock.get_component_version.side_effect = all_components_version_entities

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)

    # ACT
    update_component_version_command_handler.handle(
        command=update_component_version_with_dependencies_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    component_version_entity_to_be_updated.lastUpdatedBy = (
        update_component_version_with_dependencies_command_mock.lastUpdatedBy.value
    )
    component_version_entity_to_be_updated.lastUpdateDate = "2023-10-12T00:00:00+00:00"
    component_version_entity_to_be_updated.componentVersionDependencies = [
        ComponentVersionEntry(
            componentId="comp-1234abc",
            componentName="component-1234abc",
            componentVersionId="vers-1234abc",
            componentVersionName="1.0.0",
            order=1,
        ),
        ComponentVersionEntry(
            componentId="comp-123def",
            componentName="component-1234def",
            componentVersionId="vers-1234def",
            componentVersionName="2.0.0",
            order=2,
        ),
        ComponentVersionEntry(
            componentId="comp-123ghi",
            componentName="component-1234ghi",
            componentVersionId="vers-1234ghi",
            componentVersionName="3.0.0",
            order=3,
        ),
    ]
    component_version_entity_to_be_updated.componentVersionName = expected_version_name
    component_version_entity_to_be_updated.componentVersionDescription = (
        update_component_version_with_dependencies_command_mock.componentVersionDescription.value
    )
    component_version_entity_to_be_updated.softwareVendor = (
        update_component_version_with_dependencies_command_mock.softwareVendor.value
    )
    component_version_entity_to_be_updated.softwareVersion = (
        update_component_version_with_dependencies_command_mock.softwareVersion.value
    )
    component_version_entity_to_be_updated.licenseDashboard = None
    component_version_entity_to_be_updated.notes = None
    component_version_entity_to_be_updated.status = component_version.ComponentVersionStatus.Updating
    component_version_repo_mock.update_entity.assert_called_once_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=update_component_version_with_dependencies_command_mock.componentId.value,
            componentVersionId=update_component_version_with_dependencies_command_mock.componentVersionId.value,
        ),
        component_version_entity_to_be_updated,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        component_version_update_started.ComponentVersionUpdateStarted(
            component_id="comp-1234abcd",
            component_version_id="vers-1234abcd",
            component_version_description="Test description",
            component_version_name=expected_version_name,
            component_version_dependencies=[
                ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                ComponentVersionEntry(
                    componentId="comp-123def",
                    componentName="component-1234def",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    order=2,
                ),
                ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    order=3,
                ),
            ],
            component_version_yaml_definition=get_test_component_yaml_definition(),
            previous_component_version_dependencies=[],
        )
    )


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name, component_status, error_message",
    (
        (
            "2.0.0-rc.1",
            "2.0.0-rc.2",
            component_version.ComponentVersionStatus.Failed,
            f"Version vers-1234abc of "
            f"component comp-1234abc is"
            f" not in a valid status: "
            f"{component_version.ComponentVersionStatus.Failed}.",
        ),
        (
            "2.1.0-rc.1",
            "2.1.0-rc.2",
            component_version.ComponentVersionStatus.Created,
            f"Version vers-1234abc of "
            f"component comp-1234abc "
            f"is not in a valid "
            f"status: "
            f"{component_version.ComponentVersionStatus.Created}.",
        ),
        (
            "2.0.1-rc.1",
            "2.0.1-rc.2",
            component_version.ComponentVersionStatus.Creating,
            f"Version vers-1234abc of "
            f"component comp-1234abc "
            f"is not in a valid "
            f"status: "
            f"{component_version.ComponentVersionStatus.Creating}.",
        ),
    ),
)
@freeze_time("2023-10-12")
def test_fail_update_component_version_when_dependent_component_version_is_not_validated_or_released(
    fetched_release_name,
    expected_version_name,
    update_component_version_with_dependencies_command_mock,
    component_version_query_service_mock,
    return_dependent_component_version_for_update,
    component_status,
    error_message,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    all_components = [
        {
            "componentId": update_component_version_with_dependencies_command_mock.componentId.value,
            "componentVersionId": update_component_version_with_dependencies_command_mock.componentVersionId.value,
            "componentName": "test-component",
            "status": component_version.ComponentVersionStatus.Validated.value,
            "versionName": fetched_release_name,
        }
    ]
    for dep in update_component_version_with_dependencies_command_mock.componentVersionDependencies.value:
        all_components.append(
            {
                "componentId": dep.componentId,
                "componentVersionId": dep.componentVersionId,
                "componentName": dep.componentName,
                "status": component_status,
            }
        )
    component_version_query_service_mock.get_component_version.side_effect = (
        return_dependent_component_version_for_update(
            componentName=item.get("componentName"),
            componentId=item.get("componentId"),
            componentVersionId=item.get("componentVersionId"),
            status=item.get("status"),
            versionName=item.get("versionName", None),
        )
        for item in all_components
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_command_handler.handle(
            command=update_component_version_with_dependencies_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(error_message)


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name,component_id,error_message",
    (
        (
            "2.0.0-rc.1",
            "2.0.0-rc.2",
            None,
            "Version vers-1234abc of component comp-1234abc does not exist.",
        ),
        ("2.1.0-rc.1", "2.1.0-rc.2", "not_none", None),
        (
            "2.0.1-rc.1",
            "2.0.1-rc.2",
            None,
            "Version vers-1234abc of component comp-1234abc does not exist.",
        ),
    ),
)
def test_should_fail_if_dependent_component_does_not_exist(
    fetched_release_name,
    expected_version_name,
    update_component_version_with_dependencies_command_mock,
    component_version_query_service_mock,
    return_dependent_component_version_for_update,
    error_message,
    component_id,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    all_components = [
        {
            "componentId": update_component_version_with_dependencies_command_mock.componentId.value,
            "componentVersionId": update_component_version_with_dependencies_command_mock.componentVersionId.value,
            "componentName": "test-component",
            "status": component_version.ComponentVersionStatus.Validated.value,
            "versionName": fetched_release_name,
        }
    ]
    for dep in update_component_version_with_dependencies_command_mock.componentVersionDependencies.value:
        all_components.append(
            {
                "componentId": (dep.componentId if component_id is not None else component_id),
                "componentVersionId": dep.componentVersionId,
                "componentName": dep.componentName,
                "status": component_version.ComponentVersionStatus.Validated,
            }
        )
    component_version_query_service_mock.get_component_version.side_effect = (
        return_dependent_component_version_for_update(
            componentName=item.get("componentName"),
            componentId=item.get("componentId"),
            componentVersionId=item.get("componentVersionId"),
            status=item.get("status"),
            versionName=item.get("versionName", None),
        )
        for item in all_components
    )

    # ACT
    if component_id:
        update_component_version_command_handler.handle(
            command=update_component_version_with_dependencies_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

        # ASSERT
        uow_mock.commit.assert_called()

    else:
        with pytest.raises(domain_exception.DomainException) as e:
            update_component_version_command_handler.handle(
                command=update_component_version_with_dependencies_command_mock,
                uow=uow_mock,
                message_bus=message_bus_mock,
                component_version_qry_srv=component_version_query_service_mock,
            )

        # ASSERT
        assertpy.assert_that(str(e.value)).is_equal_to(error_message)


@pytest.fixture()
def update_component_version_with_dependencies_same_as_updating_component_command_mock(
    get_test_component_yaml_definition,
) -> update_component_version_command.UpdateComponentVersionCommand:
    return update_component_version_command.UpdateComponentVersionCommand(
        componentId=component_id_value_object.from_str("comp-1234abcd"),
        componentVersionId=component_version_id_value_object.from_str("vers-1234abcd"),
        componentVersionDescription=component_version_description_value_object.from_str("Test description"),
        componentVersionDependencies=component_version_dependencies_value_object.from_list(
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-123ghi",
                    componentName="component-1234ghi",
                    componentVersionId="vers-1234ghi",
                    componentVersionName="3.0.0",
                    order=3,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abc",
                    componentName="component-1234abc",
                    componentVersionId="vers-1234abc",
                    componentVersionName="1.0.0",
                    order=1,
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234abcd",
                    componentName="component-1234abcd",
                    componentVersionId="vers-1234def",
                    componentVersionName="2.0.0",
                    order=2,
                ),
            ]
        ),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            get_test_component_yaml_definition()
        ),
        softwareVendor=component_software_vendor_value_object.from_str("vector"),
        softwareVersion=component_software_version_value_object.from_str("1.0.0"),
        lastUpdatedBy=user_id_value_object.from_str("T000001"),
    )


@pytest.mark.parametrize(
    "fetched_release_name,expected_version_name",
    (
        ("2.0.0-rc.1", "2.0.0-rc.2"),
        ("2.1.0-rc.1", "2.1.0-rc.2"),
        ("2.0.1-rc.1", "2.0.1-rc.2"),
    ),
)
def test_should_fail_if_dependent_component_is_same_as_the_component_being_updated(
    fetched_release_name,
    expected_version_name,
    update_component_version_with_dependencies_same_as_updating_component_command_mock,
    component_version_query_service_mock,
    return_dependent_component_version_for_update,
):
    # ARRANGE
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)

    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    all_components = [
        {
            "componentId": update_component_version_with_dependencies_same_as_updating_component_command_mock.componentId.value,
            "componentVersionId": update_component_version_with_dependencies_same_as_updating_component_command_mock.componentVersionId.value,
            "componentName": "test-component",
            "status": component_version.ComponentVersionStatus.Validated.value,
            "versionName": fetched_release_name,
        }
    ]
    for (
        dep
    ) in (
        update_component_version_with_dependencies_same_as_updating_component_command_mock.componentVersionDependencies.value
    ):
        all_components.append(
            {
                "componentId": dep.componentId,
                "componentVersionId": dep.componentVersionId,
                "componentName": dep.componentName,
                "status": component_version.ComponentVersionStatus.Validated,
            }
        )
    component_version_query_service_mock.get_component_version.side_effect = (
        return_dependent_component_version_for_update(
            componentName=item.get("componentName"),
            componentId=item.get("componentId"),
            componentVersionId=item.get("componentVersionId"),
            status=item.get("status"),
            versionName=item.get("versionName", None),
        )
        for item in all_components
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_command_handler.handle(
            command=update_component_version_with_dependencies_same_as_updating_component_command_mock,
            uow=uow_mock,
            message_bus=message_bus_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Component {update_component_version_with_dependencies_same_as_updating_component_command_mock.componentId.value} cannot be a dependency of itself."
    )


@freeze_time("2023-10-12")
def test_handle_should_succeed_when_updating_downstream_dependencies(
    update_component_version_without_dependencies_command_mock,
    component_version_query_service_mock,
    get_test_component_yaml_definition,
    get_mock_components_versions_list_with_dependencies,
):
    # ARRANGE
    components_version_list = get_mock_components_versions_list_with_dependencies()
    message_bus_mock = mock.create_autospec(spec=message_bus.MessageBus)
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_version_query_service_mock.get_component_version.side_effect = components_version_list
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    expected_version_name = "1.0.0-rc.2"

    # ACT
    update_component_version_command_handler.handle(
        command=update_component_version_without_dependencies_command_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    uow_mock.commit.assert_called()
    assertpy.assert_that(component_version_repo_mock.update_entity.call_count).is_equal_to(4)
    component_version_repo_mock.update_entity.assert_has_calls(
        [
            mock.call(
                component_version.ComponentVersionPrimaryKey(
                    componentId=f"comp-{i}",
                    componentVersionId=f"vers-{i}",
                ),
                component_version.ComponentVersion(
                    componentId=f"comp-{i}",
                    componentName=f"component-{i}",
                    componentVersionId=f"vers-{i}",
                    componentVersionName="1.0.0-rc.1",
                    componentVersionDescription="Test component version",
                    componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/comp-{i}/1.0.0-rc.1/1",
                    componentVersionS3Uri=f"s3://test-component-bucket/comp-{i}/1.0.0-rc.1/component.yaml",
                    componentPlatform="Linux",
                    componentSupportedArchitectures=["amd64", "arm64"],
                    componentSupportedOsVersions=["Ubuntu 24"],
                    componentVersionDependencies=[
                        ComponentVersionEntry(
                            componentId=TEST_COMPONENT_ID,
                            componentName=TEST_COMPONENT_NAME,
                            componentVersionId=TEST_COMPONENT_VERSION_ID,
                            componentVersionName=expected_version_name,
                            order=1,
                        )
                    ],
                    softwareVendor="Vector",
                    softwareVersion="1.0.0",
                    licenseDashboard=None,
                    notes=None,
                    status="VALIDATED",
                    createDate="2024-01-11",
                    createdBy="2024-01-11",
                    lastUpdateDate="2024-01-11",
                    lastUpdatedBy="T0000001",
                ),
            )
            for i in range(3)
        ],
        any_order=False,
    )

    message_bus_mock.publish.assert_called_once_with(
        component_version_update_started.ComponentVersionUpdateStarted(
            component_id=TEST_COMPONENT_ID,
            component_version_id=TEST_COMPONENT_VERSION_ID,
            component_version_description="Test description",
            component_version_name=expected_version_name,
            component_version_dependencies=[],
            component_version_yaml_definition=get_test_component_yaml_definition(),
            previous_component_version_dependencies=[],
        )
    )


@freeze_time("2023-10-12")
def test_handle_should_succeed_when_updating_downstream_dependencies_function_only(
    component_version_query_service_mock,
    get_mock_components_versions_list_with_dependencies,
):
    # ARRANGE
    components_version_list = get_mock_components_versions_list_with_dependencies()
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_version_query_service_mock.get_component_version.side_effect = components_version_list[1:]
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    expected_version_name = "1.0.0-rc.2"

    # ACT
    update_component_version_command_handler.__update_downstream_dependencies(
        update_component_version_name=expected_version_name,
        component_version_entity=components_version_list[0],
        uow=uow_mock,
        component_version_qry_srv=component_version_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(component_version_repo_mock.update_entity.call_count).is_equal_to(3)
    component_version_repo_mock.update_entity.assert_has_calls(
        [
            mock.call(
                component_version.ComponentVersionPrimaryKey(
                    componentId=f"comp-{i}",
                    componentVersionId=f"vers-{i}",
                ),
                component_version.ComponentVersion(
                    componentId=f"comp-{i}",
                    componentName=f"component-{i}",
                    componentVersionId=f"vers-{i}",
                    componentVersionName="1.0.0-rc.1",
                    componentVersionDescription="Test component version",
                    componentBuildVersionArn=f"arn:aws:imagebuilder:us-east-1:123456789012:component/comp-{i}/1.0.0-rc.1/1",
                    componentVersionS3Uri=f"s3://test-component-bucket/comp-{i}/1.0.0-rc.1/component.yaml",
                    componentPlatform="Linux",
                    componentSupportedArchitectures=["amd64", "arm64"],
                    componentSupportedOsVersions=["Ubuntu 24"],
                    componentVersionDependencies=[
                        ComponentVersionEntry(
                            componentId=TEST_COMPONENT_ID,
                            componentName=TEST_COMPONENT_NAME,
                            componentVersionId=TEST_COMPONENT_VERSION_ID,
                            componentVersionName=expected_version_name,
                            order=1,
                        ),
                    ],
                    softwareVendor="Vector",
                    softwareVersion="1.0.0",
                    status="VALIDATED",
                    createDate="2024-01-11",
                    createdBy="2024-01-11",
                    lastUpdateDate="2024-01-11",
                    lastUpdatedBy="T0000001",
                ),
            )
            for i in range(3)
        ],
        any_order=False,
    )


@freeze_time("2023-10-12")
def test_handle_should_fail_when_no_component_is_returned_updating_downstream_dependencies(
    component_version_query_service_mock,
    get_mock_components_versions_list_with_dependencies,
):
    # ARRANGE
    components_version_list = get_mock_components_versions_list_with_dependencies()
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    component_version_query_service_mock.get_component_version.return_value = None
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk, x: repos_dict.get(x)
    expected_version_name = "1.0.0-rc.1"

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_component_version_command_handler.__update_downstream_dependencies(
            update_component_version_name=expected_version_name,
            component_version_entity=components_version_list[0],
            uow=uow_mock,
            component_version_qry_srv=component_version_query_service_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Version vers-0 of component comp-0 does not exist.")
