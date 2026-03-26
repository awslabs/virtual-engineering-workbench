from datetime import datetime, timezone
from itertools import product

from app.packaging.domain.commands.component import launch_component_version_testing_environment_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version, component_version_test_execution
from app.packaging.domain.ports import component_query_service, component_version_testing_service
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_image_upstream_id_value_object,
    component_version_test_execution_instance_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: launch_component_version_testing_environment_command.LaunchComponentVersionTestingEnvironmentCommand,
    component_qry_srv: component_query_service.ComponentQueryService,
    component_version_testing_srv: component_version_testing_service.ComponentVersionTestingService,
    uow: unit_of_work.UnitOfWork,
):
    component_entity = component_qry_srv.get_component(command.componentId.value)

    if component_entity is None:
        raise domain_exception.DomainException(f"Component {command.componentId.value} does not exist.")

    with uow:
        uow.get_repository(
            component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
        ).update_attributes(
            component_version.ComponentVersionPrimaryKey(
                componentId=command.componentId.value,
                componentVersionId=command.componentVersionId.value,
            ),
            status=component_version.ComponentVersionStatus.Testing,
        )
        uow.commit()

    for supported_architecture, supported_os_version in product(
        component_entity.componentSupportedArchitectures, component_entity.componentSupportedOsVersions
    ):
        image_upstream_id = component_version_test_execution_image_upstream_id_value_object.from_str(
            component_version_testing_srv.get_testing_environment_image_upstream_id(
                architecture=supported_architecture,
                platform=component_entity.componentPlatform,
                os_version=supported_os_version,
            )
        ).value
        # We are not validating this (for now) since it requires
        # performing API calls at runtime. Moreover,
        # this is a configuration parameter under our control
        instance_type = component_version_testing_srv.get_testing_environment_instance_type(
            architecture=supported_architecture,
            platform=component_entity.componentPlatform,
            os_version=supported_os_version,
        )
        instance_id = component_version_test_execution_instance_id_value_object.from_str(
            component_version_testing_srv.launch_testing_environment(
                image_upstream_id=image_upstream_id, instance_type=instance_type
            )
        ).value
        current_time = datetime.now(timezone.utc).isoformat()
        component_version_test_execution_entity = component_version_test_execution.ComponentVersionTestExecution(
            componentVersionId=command.componentVersionId.value,
            testExecutionId=command.testExecutionId.value,
            instanceId=instance_id,
            instanceArchitecture=supported_architecture,
            instanceImageUpstreamId=image_upstream_id,
            instanceOsVersion=supported_os_version,
            instancePlatform=component_entity.componentPlatform,
            # When we launch the instance it starts in DISCONNECTED status
            instanceStatus=component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected.value,
            createDate=current_time,
            lastUpdateDate=current_time,
            status=component_version_test_execution.ComponentVersionTestExecutionStatus.Pending.value,
        )

        with uow:
            uow.get_repository(
                repo_key=component_version_test_execution.ComponentVersionTestExecutionPrimaryKey,
                repo_type=component_version_test_execution.ComponentVersionTestExecution,
            ).add(component_version_test_execution_entity)
            uow.commit()
