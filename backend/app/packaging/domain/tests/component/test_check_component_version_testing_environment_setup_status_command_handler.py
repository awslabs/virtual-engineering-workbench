import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.component import (
    check_component_version_testing_environment_setup_status_command_handler,
)
from app.packaging.domain.commands.component import (
    check_component_version_testing_environment_setup_status_command,
)
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
)


@pytest.fixture()
def check_component_version_testing_environment_setup_status_command_mock(
    get_test_component_version_id, get_test_test_execution_id
) -> (
    check_component_version_testing_environment_setup_status_command.CheckComponentVersionTestingEnvironmentSetupStatusCommand
):
    return check_component_version_testing_environment_setup_status_command.CheckComponentVersionTestingEnvironmentSetupStatusCommand(
        componentVersionId=component_version_id_value_object.from_str(get_test_component_version_id),
        testExecutionId=component_version_test_execution_id_value_object.from_str(get_test_test_execution_id),
    )


@pytest.fixture
def get_test_component_version_test_execution_with_specific_instance_id_and_setup_command(
    get_test_component_version_id, get_test_test_execution_id
):
    def _get_test_component_version_test_execution_with_specific_instance_id_and_setup_command(
        instance_id: str,
        setup_command_id: str,
        setup_command_status: str,
        test_status: str,
    ):
        return component_version_test_execution.ComponentVersionTestExecution(
            componentVersionId=get_test_component_version_id,
            testExecutionId=get_test_test_execution_id,
            instanceId=instance_id,
            instanceArchitecture="amd64",
            instanceImageUpstreamId="ami-01234567890abcdef",
            instanceOsVersion="Ubuntu 24",
            instancePlatform="Linux",
            instanceStatus="CONNECTED",
            setupCommandId=setup_command_id,
            setupCommandStatus=setup_command_status,
            createDate="2000-01-01",
            lastUpdateDate="2000-01-01",
            status=test_status,
        )

    return _get_test_component_version_test_execution_with_specific_instance_id_and_setup_command


@pytest.mark.parametrize(
    "instance_ids, command_executions, desired_aggregate_command_status",
    (
        (
            ["i-01234567890abcdef"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
        ),
        (
            ["i-01234567890abcdef"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
        ),
        (
            ["i-01234567890abcdef"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
        ),
        (
            ["i-01234567890abcdef", "i-01234567890ghijkl"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                },
                "ef7fdfd8-9b57-4151-a15c-111111111111": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
        ),
        (
            ["i-01234567890abcdef", "i-01234567890ghijkl"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                },
                "ef7fdfd8-9b57-4151-a15c-111111111111": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
        ),
        (
            ["i-01234567890abcdef", "i-01234567890ghijkl"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                },
                "ef7fdfd8-9b57-4151-a15c-111111111111": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
        ),
        (
            ["i-01234567890abcdef", "i-01234567890ghijkl"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                },
                "ef7fdfd8-9b57-4151-a15c-111111111111": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
        ),
        (
            ["i-01234567890abcdef", "i-01234567890ghijkl"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                },
                "ef7fdfd8-9b57-4151-a15c-111111111111": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
        ),
        (
            ["i-01234567890abcdef", "i-01234567890ghijkl"],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                },
                "ef7fdfd8-9b57-4151-a15c-111111111111": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
        ),
        (
            [
                "i-01234567890abcdef",
                "i-01234567890ghijkl",
                "i-56789012345abcdef",
                "i-56789012345ghijkl",
            ],
            {
                "ef7fdfd8-9b57-4151-a15c-000000000000": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                },
                "ef7fdfd8-9b57-4151-a15c-111111111111": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                },
                "ef7fdfd8-9b57-4151-a15c-222222222222": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
                },
                "ef7fdfd8-9b57-4151-a15c-333333333333": {
                    "current_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                    "previous_command_status": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
                },
            },
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
        ),
    ),
)
@freeze_time("2023-09-29")
def test_handle_should_check_component_version_testing_environment_setup_status(
    check_component_version_testing_environment_setup_status_command_mock,
    get_test_component_version_test_execution_with_specific_instance_id_and_setup_command,
    component_version_test_execution_query_service_mock,
    generic_repo_mock,
    component_version_testing_service_mock,
    uow_mock,
    instance_ids,
    command_executions,
    desired_aggregate_command_status,
    get_test_component_version_id,
    get_test_test_execution_id,
):
    # ARRANGE
    component_version_test_execution_query_service_mock.get_component_version_test_executions_by_test_execution_id.return_value = [
        get_test_component_version_test_execution_with_specific_instance_id_and_setup_command(
            instance_id=instance_id,
            setup_command_id=command_id,
            setup_command_status=command_executions[command_id].get("previous_command_status"),
            test_status=component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running,
        )
        for command_id, instance_id in zip(command_executions.keys(), instance_ids)
    ]
    component_version_testing_service_mock.get_testing_command_status.side_effect = [
        command_executions[command_id].get("current_command_status")
        for command_id in command_executions.keys()
        if command_executions[command_id].get("previous_command_status")
        not in [
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
        ]
    ]

    # ACT
    testing_environment_setup_command_status = (
        check_component_version_testing_environment_setup_status_command_handler.handle(
            command=check_component_version_testing_environment_setup_status_command_mock,
            component_version_test_execution_qry_srv=component_version_test_execution_query_service_mock,
            component_version_testing_srv=component_version_testing_service_mock,
            uow=uow_mock,
        )
    )

    # ASSERT
    assertpy.assert_that(testing_environment_setup_command_status).is_equal_to(desired_aggregate_command_status)
    for command_id, instance_id in zip(command_executions.keys(), instance_ids):
        current_command_status = command_executions[command_id].get("current_command_status")
        previous_command_status = command_executions[command_id].get("previous_command_status")

        if (
            desired_aggregate_command_status
            == component_version_test_execution.ComponentVersionTestExecutionStatus.Failed
            and current_command_status
            not in [
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
            ]
        ):
            update_attributes = {
                "setupCommandStatus": component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
                "status": component_version_test_execution.ComponentVersionTestExecutionStatus.Failed,
            }

            generic_repo_mock.update_attributes.assert_any_call(
                component_version_test_execution.ComponentVersionTestExecutionPrimaryKey(
                    componentVersionId=get_test_component_version_id,
                    testExecutionId=get_test_test_execution_id,
                    instanceId=instance_id,
                ),
                lastUpdateDate="2023-09-29T00:00:00+00:00",
                **update_attributes,
            )
            uow_mock.commit.assert_called()

        if previous_command_status not in [
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
        ]:
            component_version_testing_service_mock.get_testing_command_status.assert_any_call(
                command_id=command_id,
                instance_id=instance_id,
            )

            update_attributes = {"setupCommandStatus": current_command_status}
            if (
                current_command_status
                == component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed
            ):
                update_attributes["status"] = (
                    component_version_test_execution.ComponentVersionTestExecutionStatus.Failed
                )

            generic_repo_mock.update_attributes.assert_any_call(
                component_version_test_execution.ComponentVersionTestExecutionPrimaryKey(
                    componentVersionId=get_test_component_version_id,
                    testExecutionId=get_test_test_execution_id,
                    instanceId=instance_id,
                ),
                lastUpdateDate="2023-09-29T00:00:00+00:00",
                **update_attributes,
            )
            uow_mock.commit.assert_called()
