from datetime import datetime, timedelta, timezone

from app.packaging.domain.commands.component import check_component_version_testing_environment_launch_status_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.ports import component_version_test_execution_query_service, component_version_testing_service
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_instance_status_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __update_attributes(
    command: check_component_version_testing_environment_launch_status_command.CheckComponentVersionTestingEnvironmentLaunchStatusCommand,
    uow: unit_of_work.UnitOfWork,
    instance_id: str,
    instanceStatus: str,
    status: str,
):
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
            instanceStatus=instanceStatus,
            lastUpdateDate=datetime.now(timezone.utc).isoformat(),
            status=status,
        )
        uow.commit()


def handle(
    command: check_component_version_testing_environment_launch_status_command.CheckComponentVersionTestingEnvironmentLaunchStatusCommand,
    component_version_test_execution_qry_srv: component_version_test_execution_query_service.ComponentVersionTestExecutionQueryService,
    component_version_testing_srv: component_version_testing_service.ComponentVersionTestingService,
    uow: unit_of_work.UnitOfWork,
):
    component_version_test_execution_entities = (
        component_version_test_execution_qry_srv.get_component_version_test_executions_by_test_execution_id(
            version_id=command.componentVersionId.value, test_execution_id=command.testExecutionId.value
        )
    )
    instance_ids = [
        component_version_test_execution_entity.instanceId
        for component_version_test_execution_entity in component_version_test_execution_entities
    ]

    aggregated_environment_status = (
        component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected
    )

    for instance_id in instance_ids:
        environment_status = component_version_test_execution_instance_status_value_object.from_str(
            component_version_testing_srv.get_testing_environment_status(instance_id=instance_id)
        ).value

        match environment_status:
            case component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected:
                aggregated_environment_status = (
                    component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected
                )
                current_timestamp = datetime.now()
                # If an instance is not CONNECTED after 5 minutes we time out
                if abs(
                    current_timestamp
                    - datetime.strptime(
                        component_version_testing_srv.get_testing_environment_creation_time(instance_id=instance_id),
                        "%Y-%m-%d %H:%M:%S",
                    )
                ) > timedelta(minutes=5):
                    __update_attributes(
                        command=command,
                        uow=uow,
                        instance_id=instance_id,
                        instanceStatus=environment_status,
                        status=component_version_test_execution.ComponentVersionTestExecutionStatus.Failed.value,
                    )
                    raise domain_exception.DomainException("Testing environment launch has timed out.")
            case component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Connected:
                __update_attributes(
                    command=command,
                    uow=uow,
                    instance_id=instance_id,
                    instanceStatus=environment_status,
                    status=component_version_test_execution.ComponentVersionTestExecutionStatus.Running.value,
                )

    return aggregated_environment_status
