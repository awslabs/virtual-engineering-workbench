from app.packaging.domain.model.recipe import recipe_version_test_execution_summary
from app.packaging.domain.ports import component_version_definition_service, recipe_version_test_execution_query_service
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_id_value_object,
)


class RecipeVersionTestExecutionDomainQueryService:
    def __init__(
        self,
        recipe_version_test_execution_qry_srv: recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService,
        component_version_definition_srv: component_version_definition_service.ComponentVersionDefinitionService,
    ):
        self._recipe_version_test_execution_qry_srv = recipe_version_test_execution_qry_srv
        self._component_version_definition_srv = component_version_definition_srv

    def get_recipe_version_test_execution_summaries(
        self, version_id: recipe_version_id_value_object.RecipeVersionIdValueObject
    ):
        recipe_version_test_executions = self._recipe_version_test_execution_qry_srv.get_recipe_version_test_executions(
            version_id=version_id.value
        )
        recipe_version_test_execution_summaries = []

        for test_execution in recipe_version_test_executions:
            recipe_version_test_execution_summaries.append(
                recipe_version_test_execution_summary.RecipeVersionTestExecutionSummary(
                    recipeVersionId=test_execution.recipeVersionId,
                    instanceArchitecture=test_execution.instanceArchitecture,
                    instanceImageUpstreamId=test_execution.instanceImageUpstreamId,
                    instanceOsVersion=test_execution.instanceOsVersion,
                    instancePlatform=test_execution.instancePlatform,
                    status=test_execution.status,
                    testExecutionId=test_execution.testExecutionId,
                    instanceId=test_execution.instanceId,
                    createDate=test_execution.createDate,
                    lastUpdateDate=test_execution.lastUpdateDate,
                )
            )

        return recipe_version_test_execution_summaries

    def get_recipe_version_test_execution(
        self,
        version_id: recipe_version_id_value_object.RecipeVersionIdValueObject,
        test_execution_id: recipe_version_test_execution_id_value_object.RecipeVersionTestExecutionIdValueObject,
    ):
        return self._recipe_version_test_execution_qry_srv.get_recipe_version_test_execution(
            version_id=version_id.value, test_execution_id=test_execution_id.value
        )

    def get_recipe_version_test_execution_logs_url(
        self,
        version_id: recipe_version_id_value_object.RecipeVersionIdValueObject,
        test_execution_id: recipe_version_test_execution_id_value_object.RecipeVersionTestExecutionIdValueObject,
    ):
        test_execution = self._recipe_version_test_execution_qry_srv.get_recipe_version_test_execution(
            version_id=version_id.value, test_execution_id=test_execution_id.value
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
