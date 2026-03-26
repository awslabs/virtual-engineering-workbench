import logging
from datetime import datetime, timezone

from app.packaging.domain.commands.component import setup_component_version_testing_environment_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.ports import component_version_test_execution_query_service, component_version_testing_service
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_command_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: setup_component_version_testing_environment_command.SetupComponentVersionTestingEnvironmentCommand,
    component_version_test_execution_qry_srv: component_version_test_execution_query_service.ComponentVersionTestExecutionQueryService,
    component_version_testing_srv: component_version_testing_service.ComponentVersionTestingService,
    logger: logging.Logger,
    uow: unit_of_work.UnitOfWork,
):
    component_version_test_execution_entities = (
        component_version_test_execution_qry_srv.get_component_version_test_executions_by_test_execution_id(
            version_id=command.componentVersionId.value, test_execution_id=command.testExecutionId.value
        )
    )
    for component_version_test_execution_entity in component_version_test_execution_entities:
        try:
            setup_command_id = component_version_test_execution_command_id_value_object.from_str(
                component_version_testing_srv.setup_testing_environment(
                    architecture=component_version_test_execution_entity.instanceArchitecture,
                    instance_id=component_version_test_execution_entity.instanceId,
                    os_version=component_version_test_execution_entity.instanceOsVersion,
                    platform=component_version_test_execution_entity.instancePlatform,
                )
            ).value
            current_time = datetime.now(timezone.utc).isoformat()

            with uow:
                uow.get_repository(
                    component_version_test_execution.ComponentVersionTestExecutionPrimaryKey,
                    component_version_test_execution.ComponentVersionTestExecution,
                ).update_attributes(
                    component_version_test_execution.ComponentVersionTestExecutionPrimaryKey(
                        componentVersionId=command.componentVersionId.value,
                        testExecutionId=command.testExecutionId.value,
                        instanceId=component_version_test_execution_entity.instanceId,
                    ),
                    setupCommandId=setup_command_id,
                    # When we send the command it starts in PENDING status
                    setupCommandStatus=component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                    lastUpdateDate=current_time,
                    status=component_version_test_execution.ComponentVersionTestExecutionStatus.Running,
                )
                uow.commit()
        except Exception as e:
            error_msg = f"Testing environment setup failed for {component_version_test_execution_entity.instanceId}."

            logger.exception(error_msg)

            raise domain_exception.DomainException(error_msg) from e
