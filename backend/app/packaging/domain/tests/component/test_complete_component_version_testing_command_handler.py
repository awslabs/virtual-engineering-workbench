import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    complete_component_version_testing_command_handler,
)
from app.packaging.domain.commands.component import (
    complete_component_version_testing_command,
)
from app.packaging.domain.events.recipe import (
    recipe_version_update_on_component_update_requested,
)
from app.packaging.domain.model.component import (
    component_version,
    component_version_test_execution,
)
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
)

TEST_COMPONENT_ID = "comp-1234abcd"
TEST_COMPONENT_VERSION_ID = "vers-1234abcd"
TEST_TEST_EXECUTION_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"


@pytest.fixture()
def complete_component_version_testing_command_mock() -> (
    complete_component_version_testing_command.CompleteComponentVersionTestingCommand
):
    return complete_component_version_testing_command.CompleteComponentVersionTestingCommand(
        componentId=component_id_value_object.from_str(TEST_COMPONENT_ID),
        componentVersionId=component_version_id_value_object.from_str(TEST_COMPONENT_VERSION_ID),
        testExecutionId=component_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture
def get_test_component_version_test_execution_with_specific_instance_id_and_test_command_status():
    def _get_test_component_version_test_execution_with_specific_instance_id_and_test_command_status(
        instance_id: str, test_command_status: str
    ):
        return component_version_test_execution.ComponentVersionTestExecution(
            componentVersionId=TEST_COMPONENT_VERSION_ID,
            testExecutionId=TEST_TEST_EXECUTION_ID,
            instanceId=instance_id,
            instanceArchitecture="amd64",
            instanceImageUpstreamId="ami-01234567890abcdef",
            instanceOsVersion="Ubuntu 24",
            instancePlatform="Linux",
            instanceStatus="CONNECTED",
            setupCommandError="This is an example error",
            setupCommandId="ef7fdfd8-9b57-4151-a15c-888888888888",
            setupCommandOutput="This is an example output",
            setupCommandStatus="SUCCESS",
            testCommandError="This is an example error",
            testCommandId="ef7fdfd8-9b57-4151-a15c-999999999999",
            testCommandOutput="This is an example output",
            testCommandStatus=test_command_status,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=component_version_test_execution.ComponentVersionTestExecutionStatus.Pending.value,
        )

    return _get_test_component_version_test_execution_with_specific_instance_id_and_test_command_status


@pytest.mark.parametrize(
    "platform, supported_architectures, supported_os_versions, instance_ids, desired_command_status",
    (
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            [component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success],
        ),
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            [
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
            ],
        ),
        (
            "Linux",
            ["amd64", "arm64"],
            ["Ubuntu 24"],
            [
                "i-01234567890abcdef",
                "i-56789012345abcdef",
            ],
            [
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
            ],
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_successfully_complete_component_version_testing(
    complete_component_version_testing_command_mock,
    component_query_service_mock,
    component_version_test_execution_query_service_mock,
    component_version_testing_service_mock,
    generic_repo_mock,
    get_test_component_with_specific_platform_architecture_and_os_version,
    get_test_component_version_test_execution_with_specific_instance_id_and_test_command_status,
    uow_mock,
    platform,
    supported_architectures,
    supported_os_versions,
    instance_ids,
    desired_command_status,
    component_version_query_service_mock,
    message_bus_mock,
    get_test_component_version,
):
    # ARRANGE
    component_query_service_mock.get_component.return_value = (
        get_test_component_with_specific_platform_architecture_and_os_version(
            platform=platform,
            supported_architectures=supported_architectures,
            supported_os_versions=supported_os_versions,
        )
    )
    component_version_test_execution_query_service_mock.get_component_version_test_executions_by_test_execution_id.return_value = [
        get_test_component_version_test_execution_with_specific_instance_id_and_test_command_status(
            instance_id=instance_id, test_command_status=command_status
        )
        for command_status, instance_id in zip(desired_command_status, instance_ids)
    ]
    component_version_entity = get_test_component_version
    component_version_query_service_mock.get_component_version.return_value = component_version_entity

    # ACT
    complete_component_version_testing_command_handler.handle(
        command=complete_component_version_testing_command_mock,
        component_qry_srv=component_query_service_mock,
        component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
        component_version_testing_srv=component_version_testing_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    for instance_id in instance_ids:
        component_version_testing_service_mock.teardown_testing_environment.assert_any_call(instance_id=instance_id)
    generic_repo_mock.update_attributes.assert_called_with(
        component_version.ComponentVersionPrimaryKey(
            componentId=complete_component_version_testing_command_mock.componentId.value,
            componentVersionId=complete_component_version_testing_command_mock.componentVersionId.value,
        ),
        status=component_version.ComponentVersionStatus.Validated,
    )
    uow_mock.commit.assert_called()
    message_bus_mock.publish.assert_called_once_with(
        recipe_version_update_on_component_update_requested.RecipeVersionUpdateOnComponentUpdateRequested(
            component_id=component_version_entity.componentId,
            component_version_id=component_version_entity.componentVersionId,
            last_updated_by=component_version_entity.lastUpdatedBy,
        )
    )


@pytest.mark.parametrize(
    "platform, supported_architectures, supported_os_versions, instance_ids, desired_command_status",
    (
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            [component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed],
        ),
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            [
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
            ],
        ),
        (
            "Linux",
            ["amd64", "arm64"],
            ["Ubuntu 24"],
            [
                "i-01234567890abcdef",
                "i-56789012345abcdef",
            ],
            [
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
            ],
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_set_component_version_status_to_failed_if_testing_fails(
    complete_component_version_testing_command_mock,
    component_query_service_mock,
    component_version_test_execution_query_service_mock,
    generic_repo_mock,
    component_version_testing_service_mock,
    get_test_component_with_specific_platform_architecture_and_os_version,
    get_test_component_version_test_execution_with_specific_instance_id_and_test_command_status,
    uow_mock,
    platform,
    supported_architectures,
    supported_os_versions,
    instance_ids,
    desired_command_status,
    component_version_query_service_mock,
    message_bus_mock,
    get_test_component_version,
):
    # ARRANGE
    component_query_service_mock.get_component.return_value = (
        get_test_component_with_specific_platform_architecture_and_os_version(
            platform=platform,
            supported_architectures=supported_architectures,
            supported_os_versions=supported_os_versions,
        )
    )
    component_version_query_service_mock.get_component_version.return_value = get_test_component_version
    component_version_test_execution_query_service_mock.get_component_version_test_executions_by_test_execution_id.return_value = [
        get_test_component_version_test_execution_with_specific_instance_id_and_test_command_status(
            instance_id=instance_id, test_command_status=command_status
        )
        for command_status, instance_id in zip(desired_command_status, instance_ids)
    ]

    # ACT
    complete_component_version_testing_command_handler.handle(
        command=complete_component_version_testing_command_mock,
        component_qry_srv=component_query_service_mock,
        component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
        component_version_testing_srv=component_version_testing_service_mock,
        component_version_qry_srv=component_version_query_service_mock,
        uow=uow_mock,
        message_bus=message_bus_mock,
    )

    # ASSERT
    generic_repo_mock.update_attributes.assert_any_call(
        component_version.ComponentVersionPrimaryKey(
            componentId=complete_component_version_testing_command_mock.componentId.value,
            componentVersionId=complete_component_version_testing_command_mock.componentVersionId.value,
        ),
        status=component_version.ComponentVersionStatus.Failed,
    )
