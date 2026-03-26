import logging
from datetime import datetime, timezone

from app.packaging.domain.commands.recipe import run_recipe_version_testing_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version_test_execution
from app.packaging.domain.ports import (
    component_version_query_service,
    recipe_version_query_service,
    recipe_version_test_execution_query_service,
    recipe_version_testing_service,
)
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_command_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: run_recipe_version_testing_command.RunRecipeVersionTestingCommand,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    recipe_version_test_execution_qry_srv: recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService,
    recipe_version_testing_srv: recipe_version_testing_service.RecipeVersionTestingService,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    logger: logging.Logger,
    uow: unit_of_work.UnitOfWork,
):
    recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
        recipe_id=command.recipeId.value, version_id=command.recipeVersionId.value
    )
    if recipe_version_entity is None:
        raise domain_exception.DomainException(f"Recipe version {command.recipeVersionId.value} does not exist.")

    recipe_version_test_execution_entity = recipe_version_test_execution_qry_srv.get_recipe_version_test_execution(
        version_id=command.recipeVersionId.value, test_execution_id=command.testExecutionId.value
    )
    try:
        test_command_id = recipe_version_test_execution_command_id_value_object.from_str(
            recipe_version_testing_srv.run_testing(
                recipe_version_component_arn=recipe_version_entity.recipeVersionComponentArn,
                architecture=recipe_version_test_execution_entity.instanceArchitecture,
                instance_id=recipe_version_test_execution_entity.instanceId,
                os_version=recipe_version_test_execution_entity.instanceOsVersion,
                platform=recipe_version_test_execution_entity.instancePlatform,
                recipe_id=recipe_version_entity.recipeId,
                recipe_version_id=recipe_version_entity.recipeVersionId,
            )
        ).value
        current_time = datetime.now(timezone.utc).isoformat()

        with uow:
            uow.get_repository(
                recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey,
                recipe_version_test_execution.RecipeVersionTestExecution,
            ).update_attributes(
                recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey(
                    recipeVersionId=command.recipeVersionId.value, testExecutionId=command.testExecutionId.value
                ),
                testCommandId=test_command_id,
                # When we send the command it starts in PENDING status
                testCommandStatus=recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Pending,
                lastUpdateDate=current_time,
                status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
                s3LogLocation=f"s3://{recipe_version_testing_srv.get_recipe_test_bucket_name()}/{command.recipeId.value}/{command.recipeVersionId.value}/{recipe_version_test_execution_entity.instanceId}/console.log",
            )
            uow.commit()
    except Exception as e:
        error_msg = f"Running tests on {recipe_version_test_execution_entity.instanceId} for {recipe_version_entity.recipeId} failed."

        logger.exception(error_msg)

        raise domain_exception.DomainException(error_msg) from e
