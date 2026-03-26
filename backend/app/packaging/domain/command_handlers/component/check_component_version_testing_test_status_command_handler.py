from datetime import datetime, timezone

from app.packaging.domain.commands.component import check_component_version_testing_test_status_command
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.ports import component_version_test_execution_query_service, component_version_testing_service
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_command_status_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __update_attributes(
    command: check_component_version_testing_test_status_command.CheckComponentVersionTestingTestStatusCommand,
    uow: unit_of_work.UnitOfWork,
    instance_id: str,
    **update_attributes,
):
    update_attributes["lastUpdateDate"] = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(
            component_version_test_execution.ComponentVersionTestExecutionPrimaryKey,
            component_version_test_execution.ComponentVersionTestExecution,
        ).update_attributes(
            component_version_test_execution.ComponentVersionTestExecutionPrimaryKey(
                componentVersionId=command.componentVersionId.value,
                testExecutionId=command.testExecutionId.value,
                instanceId=instance_id,
            ),
            **update_attributes,
        )
        uow.commit()


def __get_aggregated_command_status(
    aggregated_command_status_count: dict[
        component_version_test_execution.ComponentVersionTestExecutionCommandStatus, int
    ],
    command_statuses: list,
):
    match aggregated_command_status_count:
        case _ if all(
            status == component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success
            for status in command_statuses
        ):
            aggregated_command_status = (
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success
            )

        case _ if all(
            status == component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed
            for status in command_statuses
        ):
            aggregated_command_status = (
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed
            )

        case _ if (
            aggregated_command_status_count.get(
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running, 0
            )
            > 0
        ):
            aggregated_command_status = (
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running
            )

        case _ if (
            aggregated_command_status_count.get(
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success, 0
            )
            > 0
            and aggregated_command_status_count.get(
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending, 0
            )
            > 0
        ):
            aggregated_command_status = (
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running
            )

        case _ if (
            aggregated_command_status_count.get(
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed, 0
            )
            > 0
            and aggregated_command_status_count.get(
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending, 0
            )
            > 0
        ):
            aggregated_command_status = (
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running
            )

        case _ if (
            aggregated_command_status_count.get(
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success, 0
            )
            > 0
            and aggregated_command_status_count.get(
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed, 0
            )
            > 0
        ):
            aggregated_command_status = (
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed
            )

        case _:
            aggregated_command_status = (
                component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending
            )

    return aggregated_command_status


def handle(
    command: check_component_version_testing_test_status_command.CheckComponentVersionTestingTestStatusCommand,
    component_version_test_execution_qry_srv: component_version_test_execution_query_service.ComponentVersionTestExecutionQueryService,
    component_version_testing_srv: component_version_testing_service.ComponentVersionTestingService,
    uow: unit_of_work.UnitOfWork,
):
    component_version_test_execution_entities = (
        component_version_test_execution_qry_srv.get_component_version_test_executions_by_test_execution_id(
            version_id=command.componentVersionId.value, test_execution_id=command.testExecutionId.value
        )
    )
    command_details = [
        (
            component_version_test_execution_entity.testCommandId,
            component_version_test_execution_entity.instanceId,
            component_version_test_execution_entity.testCommandStatus,
        )
        for component_version_test_execution_entity in component_version_test_execution_entities
    ]
    command_statuses = []

    for command_id, instance_id, previous_command_status in command_details:
        # We update only the commands that are not in a
        # terminal testCommandStatus (FAILED, SUCCESS)
        if previous_command_status not in [
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed,
            component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
        ]:
            current_command_status = component_version_test_execution_command_status_value_object.from_str(
                component_version_testing_srv.get_testing_command_status(command_id=command_id, instance_id=instance_id)
            ).value
            update_attributes = {"testCommandStatus": current_command_status}
            # For terminal testCommandStatus (FAILED, SUCCESS)
            # we set the component version test execution status
            # to the corresponding value (FAILED, SUCCESS)
            match current_command_status:
                case component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed:
                    update_attributes["status"] = (
                        component_version_test_execution.ComponentVersionTestExecutionStatus.Failed.value
                    )
                case component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success:
                    update_attributes["status"] = (
                        component_version_test_execution.ComponentVersionTestExecutionStatus.Success.value
                    )

            command_statuses.append(current_command_status)
            __update_attributes(command, uow, instance_id, **update_attributes)
        else:
            command_statuses.append(previous_command_status)

    aggregated_command_status_count = {
        component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Failed: 0,
        component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending: 0,
        component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Running: 0,
        component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success: 0,
    }
    for command_status in command_statuses:
        aggregated_command_status_count[command_status] += 1

    return __get_aggregated_command_status(aggregated_command_status_count, command_statuses)
