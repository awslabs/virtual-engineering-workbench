import logging
from datetime import datetime, timezone

from app.packaging.domain.commands.recipe import setup_recipe_version_testing_environment_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version_test_execution
from app.packaging.domain.ports import recipe_version_test_execution_query_service, recipe_version_testing_service
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_command_id_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: setup_recipe_version_testing_environment_command.SetupRecipeVersionTestingEnvironmentCommand,
    recipe_version_test_execution_qry_srv: recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService,
    recipe_version_testing_srv: recipe_version_testing_service.RecipeVersionTestingService,
    logger: logging.Logger,
    uow: unit_of_work.UnitOfWork,
):
    recipe_version_test_execution_entity = recipe_version_test_execution_qry_srv.get_recipe_version_test_execution(
        version_id=command.recipeVersionId.value, test_execution_id=command.testExecutionId.value
    )

    try:
        setup_command_id = recipe_version_test_execution_command_id_value_object.from_str(
            recipe_version_testing_srv.setup_testing_environment(
                architecture=recipe_version_test_execution_entity.instanceArchitecture,
                instance_id=recipe_version_test_execution_entity.instanceId,
                os_version=recipe_version_test_execution_entity.instanceOsVersion,
                platform=recipe_version_test_execution_entity.instancePlatform,
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
                setupCommandId=setup_command_id,
                # When we send the command it starts in PENDING status
                setupCommandStatus=recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Pending,
                lastUpdateDate=current_time,
                status=recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running,
            )
            uow.commit()
    except Exception as e:
        error_msg = f"Testing environment setup failed for {recipe_version_test_execution_entity.instanceId}."

        logger.exception(error_msg)

        raise domain_exception.DomainException(error_msg) from e
