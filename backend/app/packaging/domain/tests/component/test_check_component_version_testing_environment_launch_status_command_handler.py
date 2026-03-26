from datetime import datetime, timedelta

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    check_component_version_testing_environment_launch_status_command_handler,
)
from app.packaging.domain.commands.component import (
    check_component_version_testing_environment_launch_status_command,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
)


@pytest.fixture()
def check_component_version_testing_environment_launch_status_command_mock(
    get_test_component_version_id, get_test_test_execution_id
) -> (
    check_component_version_testing_environment_launch_status_command.CheckComponentVersionTestingEnvironmentLaunchStatusCommand
):
    return check_component_version_testing_environment_launch_status_command.CheckComponentVersionTestingEnvironmentLaunchStatusCommand(
        componentVersionId=component_version_id_value_object.from_str(get_test_component_version_id),
        testExecutionId=component_version_test_execution_id_value_object.from_str(get_test_test_execution_id),
    )


@pytest.fixture
def get_test_component_version_test_execution_with_specific_instance_id_and_status(
    get_test_component_version_id, get_test_test_execution_id
):
    def _get_test_component_version_test_execution_with_specific_instance_id_and_status(
        instance_id: str, instance_status: str, test_status: str
    ):
        return component_version_test_execution.ComponentVersionTestExecution(
            componentVersionId=get_test_component_version_id,
            testExecutionId=get_test_test_execution_id,
            instanceId=instance_id,
            instanceArchitecture="amd64",
            instanceImageUpstreamId="ami-01234567890abcdef",
            instanceOsVersion="Ubuntu 24",
            instancePlatform="Linux",
            instanceStatus=instance_status,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=test_status,
        )

    return _get_test_component_version_test_execution_with_specific_instance_id_and_status


@pytest.mark.parametrize(
    "testing_environments, desired_aggregate_environment_status",
    (
        (
            (
                {
                    "instance_id": "i-01234567890abcdef",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected,
                    "test_status": component_version_test_execution.ComponentVersionTestExecutionStatus.Running,
                },
            ),
            component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected,
        ),
        (
            (
                {
                    "instance_id": "i-01234567890abcdef",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
                    "test_status": None,
                },
            ),
            component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
        ),
        (
            (
                {
                    "instance_id": "i-01234567890abcdef",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
                    "test_status": None,
                },
                {
                    "instance_id": "i-56789012345ghijkl",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
                    "test_status": None,
                },
            ),
            component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
        ),
        (
            (
                {
                    "instance_id": "i-01234567890abcdef",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
                    "test_status": None,
                },
                {
                    "instance_id": "i-56789012345ghijkl",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected,
                    "test_status": component_version_test_execution.ComponentVersionTestExecutionStatus.Running,
                },
            ),
            component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
        ),
        (
            (
                {
                    "instance_id": "i-01234567890abcdef",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected,
                    "test_status": component_version_test_execution.ComponentVersionTestExecutionStatus.Running,
                },
                {
                    "instance_id": "i-56789012345ghijkl",
                    "instance_status": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected,
                    "test_status": component_version_test_execution.ComponentVersionTestExecutionStatus.Running,
                },
            ),
            component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected,
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_check_component_version_testing_launch_status(
    check_component_version_testing_environment_launch_status_command_mock,
    component_version_test_execution_query_service_mock,
    generic_repo_mock,
    component_version_testing_service_mock,
    get_test_component_version_test_execution_with_specific_instance_id_and_status,
    uow_mock,
    testing_environments,
    desired_aggregate_environment_status,
    get_test_component_version_id,
    get_test_test_execution_id,
):
    # ARRANGE
    component_version_test_execution_query_service_mock.get_component_version_test_executions_by_test_execution_id.return_value = [
        get_test_component_version_test_execution_with_specific_instance_id_and_status(
            instance_id=testing_env.get("instance_id"),
            instance_status=testing_env.get("instance_status"),
            test_status=(
                testing_env.get("test_status")
                if testing_env.get("test_status")
                else component_version_test_execution.ComponentVersionTestExecutionStatus.Pending
            ),
        )
        for testing_env in testing_environments
    ]

    component_version_testing_service_mock.get_testing_environment_creation_time.return_value = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    component_version_testing_service_mock.get_testing_environment_status.side_effect = [
        testing_env.get("instance_status") for testing_env in testing_environments
    ]

    # ACT
    testing_environment_launch_status = (
        check_component_version_testing_environment_launch_status_command_handler.handle(
            command=check_component_version_testing_environment_launch_status_command_mock,
            component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
            component_version_testing_srv=component_version_testing_service_mock,
            uow=uow_mock,
        )
    )

    # ASSERT
    assertpy.assert_that(testing_environment_launch_status).is_equal_to(desired_aggregate_environment_status)
    counter = 0
    for testing_env in testing_environments:
        component_version_testing_service_mock.get_testing_environment_status.assert_any_call(
            instance_id=testing_env.get("instance_id"),
        )
        if testing_env.get("test_status"):
            counter += 1
            generic_repo_mock.update_attributes.assert_any_call(
                component_version_test_execution.ComponentVersionTestExecutionPrimaryKey(
                    componentVersionId=get_test_component_version_id,
                    testExecutionId=get_test_test_execution_id,
                    instanceId=testing_env.get("instance_id"),
                ),
                instanceStatus=testing_env.get("instance_status"),
                lastUpdateDate="2023-09-29T00:00:00+00:00",
                status=testing_env.get("test_status"),
            )
    assertpy.assert_that(generic_repo_mock.update_attributes.call_count).is_equal_to(counter)
    assertpy.assert_that(uow_mock.commit.call_count).is_equal_to(counter)


@pytest.mark.parametrize(
    "testing_environments, time_delta_minutes,  test_status",
    (
        (
            {
                "i-01234567890abcdef": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
                "i-56789012345ghijkl": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
            },
            10,
            component_version_test_execution.ComponentVersionTestExecutionStatus.Failed,
        ),
        (
            {
                "i-01234567890abcdef": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected,
                "i-56789012345ghijkl": component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected,
            },
            15,
            component_version_test_execution.ComponentVersionTestExecutionStatus.Failed,
        ),
    ),
)
def test_handle_should_throw_if_launch_times_out(
    check_component_version_testing_environment_launch_status_command_mock,
    get_test_component_version_test_execution_with_specific_instance_id_and_status,
    component_version_test_execution_query_service_mock,
    component_version_testing_service_mock,
    uow_mock,
    testing_environments,
    test_status,
    time_delta_minutes,
):
    # ARRANGE
    component_version_test_execution_query_service_mock.get_component_version_test_executions_by_test_execution_id.return_value = [
        get_test_component_version_test_execution_with_specific_instance_id_and_status(
            instance_id=instance_id,
            instance_status=instance_status,
            test_status=test_status,
        )
        for instance_id, instance_status in zip(testing_environments.keys(), testing_environments.values())
    ]
    component_version_testing_service_mock.get_testing_environment_creation_time.return_value = (
        datetime.now() - timedelta(minutes=time_delta_minutes)
    ).strftime("%Y-%m-%d %H:%M:%S")
    component_version_testing_service_mock.get_testing_environment_status.side_effect = testing_environments.values()

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        check_component_version_testing_environment_launch_status_command_handler.handle(
            command=check_component_version_testing_environment_launch_status_command_mock,
            component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
            component_version_testing_srv=component_version_testing_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Testing environment launch has timed out.")
