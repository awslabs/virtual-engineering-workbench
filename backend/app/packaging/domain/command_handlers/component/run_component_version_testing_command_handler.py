import logging
from datetime import datetime, timezone

from app.packaging.domain.commands.component import run_component_version_testing_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.ports import (
    component_version_query_service,
    component_version_test_execution_query_service,
    component_version_testing_service,
)
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_command_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __get_components_versions_definitions_s3_uris(component_version_entity, component_version_qry_srv, s3_uris):
    for dependency in component_version_entity.componentVersionDependencies:
        dependency_component_version_entity = component_version_qry_srv.get_component_version(
            component_id=dependency.componentId, version_id=dependency.componentVersionId
        )
        s3_uris.append(dependency_component_version_entity.componentVersionS3Uri)
    s3_uris.append(component_version_entity.componentVersionS3Uri)
    return s3_uris


def handle(
    command: run_component_version_testing_command.RunComponentVersionTestingCommand,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    component_version_test_execution_qry_srv: component_version_test_execution_query_service.ComponentVersionTestExecutionQueryService,
    component_version_testing_srv: component_version_testing_service.ComponentVersionTestingService,
    logger: logging.Logger,
    uow: unit_of_work.UnitOfWork,
):
    component_version_entity = component_version_qry_srv.get_component_version(
        component_id=command.componentId.value, version_id=command.componentVersionId.value
    )

    if component_version_entity is None:
        raise domain_exception.DomainException(f"Component version {command.componentVersionId.value} does not exist.")

    component_version_test_execution_entities = (
        component_version_test_execution_qry_srv.get_component_version_test_executions_by_test_execution_id(
            version_id=command.componentVersionId.value, test_execution_id=command.testExecutionId.value
        )
    )
    components_versions_definitions_s3_uri = []
    __get_components_versions_definitions_s3_uris(
        component_version_entity, component_version_qry_srv, components_versions_definitions_s3_uri
    )

    for component_version_test_execution_entity in component_version_test_execution_entities:
        try:
            test_command_id = component_version_test_execution_command_id_value_object.from_str(
                component_version_testing_srv.run_testing(
                    architecture=component_version_test_execution_entity.instanceArchitecture,
                    component_version_definition_s3_uri=",".join(components_versions_definitions_s3_uri),
                    instance_id=component_version_test_execution_entity.instanceId,
                    os_version=component_version_test_execution_entity.instanceOsVersion,
                    platform=component_version_test_execution_entity.instancePlatform,
                    component_id=component_version_entity.componentId,
                    component_version_id=component_version_entity.componentVersionId,
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
                    testCommandId=test_command_id,
                    # When we send the command it starts in PENDING status
                    testCommandStatus=component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Pending,
                    lastUpdateDate=current_time,
                    status=component_version_test_execution.ComponentVersionTestExecutionStatus.Running,
                    s3LogLocation=f"s3://{component_version_testing_srv.get_component_test_bucket_name()}/{command.componentId.value}/{command.componentVersionId.value}/{component_version_test_execution_entity.instanceId}/console.log",
                )
                uow.commit()
        except Exception as e:
            error_msg = f"Running tests on {component_version_test_execution_entity.instanceId} for {component_version_entity.componentId} failed."

            logger.exception(error_msg)

            raise domain_exception.DomainException(error_msg) from e
