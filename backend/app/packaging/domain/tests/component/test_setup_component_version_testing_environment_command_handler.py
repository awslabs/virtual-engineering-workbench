import logging
from itertools import product

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    setup_component_version_testing_environment_command_handler,
)
from app.packaging.domain.commands.component import (
    setup_component_version_testing_environment_command,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
)

TEST_COMPONENT_VERSION_ID = "vers-1234abcd"
TEST_TEST_EXECUTION_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"


@pytest.fixture()
def setup_component_version_testing_environment_command_mock() -> (
    setup_component_version_testing_environment_command.SetupComponentVersionTestingEnvironmentCommand
):
    return setup_component_version_testing_environment_command.SetupComponentVersionTestingEnvironmentCommand(
        componentVersionId=component_version_id_value_object.from_str(TEST_COMPONENT_VERSION_ID),
        testExecutionId=component_version_test_execution_id_value_object.from_str(TEST_TEST_EXECUTION_ID),
    )


@pytest.fixture
def get_test_component_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform():
    def _get_test_component_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform(
        architecture: str, instance_id: str, os_version: str, platform: str
    ):
        return component_version_test_execution.ComponentVersionTestExecution(
            componentVersionId=TEST_COMPONENT_VERSION_ID,
            testExecutionId=TEST_TEST_EXECUTION_ID,
            instanceId=instance_id,
            instanceArchitecture=architecture,
            instanceImageUpstreamId="ami-01234567890abcdef",
            instanceOsVersion=os_version,
            instancePlatform=platform,
            instanceStatus="CONNECTED",
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=component_version_test_execution.ComponentVersionTestExecutionStatus.Running.value,
        )

    return _get_test_component_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform


@pytest.mark.parametrize(
    "platform, supported_architectures, supported_os_versions, instance_ids, desired_command_ids",
    (
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            ["ef7fdfd8-9b57-4151-a15c-000000000000"],
        ),
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            ["ef7fdfd8-9b57-4151-a15c-000000000000"],
        ),
        (
            "Linux",
            ["amd64", "arm64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef", "i-56789012345abcdef"],
            [
                "ef7fdfd8-9b57-4151-a15c-000000000000",
                "ef7fdfd8-9b57-4151-a15c-222222222222",
            ],
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_setup_component_version_testing_environment(
    generic_repo_mock,
    component_version_test_execution_query_service_mock,
    component_version_testing_service_mock,
    get_test_component_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform,
    setup_component_version_testing_environment_command_mock,
    uow_mock,
    platform,
    supported_architectures,
    supported_os_versions,
    instance_ids,
    desired_command_ids,
):
    # ARRANGE
    component_version_test_execution_query_service_mock.get_component_version_test_executions_by_test_execution_id.return_value = [
        get_test_component_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform(
            architecture=value[0],
            instance_id=instance_ids[index],
            os_version=value[1],
            platform=platform,
        )
        for index, value in enumerate(product(supported_architectures, supported_os_versions))
    ]
    component_version_testing_service_mock.setup_testing_environment.side_effect = desired_command_ids

    # ACT
    setup_component_version_testing_environment_command_handler.handle(
        command=setup_component_version_testing_environment_command_mock,
        component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
        component_version_testing_srv=component_version_testing_service_mock,
        logger=logging.getLogger(),
        uow=uow_mock,
    )

    # ASSERT
    for index, value in enumerate(product(supported_architectures, supported_os_versions)):
        instance_id = instance_ids[index]

        component_version_testing_service_mock.setup_testing_environment.assert_any_call(
            architecture=value[0],
            instance_id=instance_id,
            os_version=value[1],
            platform=platform,
        )
        generic_repo_mock.update_attributes.assert_any_call(
            component_version_test_execution.ComponentVersionTestExecutionPrimaryKey(
                componentVersionId=TEST_COMPONENT_VERSION_ID,
                testExecutionId=TEST_TEST_EXECUTION_ID,
                instanceId=instance_id,
            ),
            setupCommandId=desired_command_ids[index],
            setupCommandStatus=component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending.value,
            lastUpdateDate="2023-09-29T00:00:00+00:00",
            status=component_version_test_execution.ComponentVersionTestExecutionStatus.Running.value,
        )
    uow_mock.commit.assert_called()


@pytest.mark.parametrize(
    "platform, supported_architectures, supported_os_versions, instance_ids, setup_results",
    (
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-1234567890"],
            [Exception("Setup failed")],
        ),
        (
            "Linux",
            ["amd64"],
            ["Ubuntu 24"],
            ["i-01234567890abcdef"],
            [Exception("Setup failed")],
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
                "ef7fdfd8-9b57-4151-a15c-000000000000",
                Exception("Setup failed"),
            ],
        ),
    ),
)
def test_handle_should_raise_exception_when_environment_setup_fails(
    get_test_component_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform,
    component_version_test_execution_query_service_mock,
    component_version_testing_service_mock,
    setup_component_version_testing_environment_command_mock,
    uow_mock,
    platform,
    supported_architectures,
    supported_os_versions,
    instance_ids,
    setup_results,
):
    # ARRANGE
    component_version_test_execution_query_service_mock.get_component_version_test_executions_by_test_execution_id.return_value = [
        get_test_component_version_test_execution_with_specific_instance_id_architecture_os_version_and_platform(
            architecture=value[0],
            instance_id=instance_ids[index],
            os_version=value[1],
            platform=platform,
        )
        for index, value in enumerate(product(supported_architectures, supported_os_versions))
    ]
    component_version_testing_service_mock.setup_testing_environment.side_effect = setup_results

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        setup_component_version_testing_environment_command_handler.handle(
            command=setup_component_version_testing_environment_command_mock,
            component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
            component_version_testing_srv=component_version_testing_service_mock,
            logger=logging.getLogger(),
            uow=uow_mock,
        )

    # ASSERT
    for instance_id, setup_result in zip(instance_ids, setup_results):
        if isinstance(setup_result, Exception):
            assertpy.assert_that(str(e.value)).is_equal_to(f"Testing environment setup failed for {instance_id}.")
