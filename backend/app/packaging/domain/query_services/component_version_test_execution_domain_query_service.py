from app.packaging.domain.model.component import component_version_test_execution_summary
from app.packaging.domain.ports import (
    component_version_definition_service,
    component_version_test_execution_query_service,
)
from app.packaging.domain.value_objects.component_version import component_version_id_value_object
from app.packaging.domain.value_objects.component_version_test_execution import (
    component_version_test_execution_id_value_object,
    component_version_test_execution_instance_id_value_object,
)


class ComponentVersionTestExecutionDomainQueryService:
    def __init__(
        self,
        component_version_test_execution_qry_srv: component_version_test_execution_query_service.ComponentVersionTestExecutionQueryService,
        component_version_definition_srv: component_version_definition_service.ComponentVersionDefinitionService,
    ):
        self._component_version_test_execution_qry_srv = component_version_test_execution_qry_srv
        self._component_version_definition_srv = component_version_definition_srv

    def get_component_version_test_execution_summaries(
        self, version_id: component_version_id_value_object.ComponentVersionIdValueObject
    ):
        component_version_test_executions = (
            self._component_version_test_execution_qry_srv.get_component_version_test_executions(
                version_id=version_id.value
            )
        )
        component_version_test_execution_summaries = []

        for test_execution in component_version_test_executions:

            component_version_test_execution_summaries.append(
                component_version_test_execution_summary.ComponentVersionTestExecutionSummary(
                    componentVersionId=test_execution.componentVersionId,
                    instanceArchitecture=test_execution.instanceArchitecture,
                    instanceId=test_execution.instanceId,
                    instanceImageUpstreamId=test_execution.instanceImageUpstreamId,
                    instanceOsVersion=test_execution.instanceOsVersion,
                    instancePlatform=test_execution.instancePlatform,
                    status=test_execution.status,
                    testExecutionId=test_execution.testExecutionId,
                    createDate=test_execution.createDate,
                    lastUpdateDate=test_execution.lastUpdateDate,
                )
            )

        return component_version_test_execution_summaries

    def get_component_version_test_executions_by_test_execution_id(
        self,
        version_id: component_version_id_value_object.ComponentVersionIdValueObject,
        test_execution_id: component_version_test_execution_id_value_object.ComponentVersionTestExecutionIdValueObject,
    ):
        return (
            self._component_version_test_execution_qry_srv.get_component_version_test_executions_by_test_execution_id(
                version_id=version_id.value, test_execution_id=test_execution_id.value
            )
        )

    def get_component_version_test_execution_logs_url(
        self,
        version_id: component_version_id_value_object.ComponentVersionIdValueObject,
        test_execution_id: component_version_test_execution_id_value_object.ComponentVersionTestExecutionIdValueObject,
        instance_id: component_version_test_execution_instance_id_value_object.ComponentVersionTestExecutionInstanceIdValueObject,
    ):
        test_execution = self._component_version_test_execution_qry_srv.get_component_version_test_execution(
            version_id=version_id.value, test_execution_id=test_execution_id.value, instance_id=instance_id.value
        )
        if test_execution.s3LogLocation is not None:
            bucket_name, _ = test_execution.s3LogLocation.split("//")[1].split("/", 1)

            s3_presigned_url = (
                test_execution.instanceId
                if bucket_name == "dummy_bucket"
                else self._component_version_definition_srv.get_s3_presigned_url(test_execution.s3LogLocation)
            )
        else:
            s3_presigned_url = ""

        return s3_presigned_url
