from datetime import datetime, timezone

from app.packaging.domain.commands.recipe import check_recipe_version_testing_test_status_command
from app.packaging.domain.model.recipe import recipe_version_test_execution
from app.packaging.domain.ports import recipe_version_test_execution_query_service, recipe_version_testing_service
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_command_status_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: check_recipe_version_testing_test_status_command.CheckRecipeVersionTestingTestStatusCommand,
    recipe_version_test_execution_qry_srv: recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService,
    recipe_version_testing_srv: recipe_version_testing_service.RecipeVersionTestingService,
    uow: unit_of_work.UnitOfWork,
):
    recipe_version_test_execution_entity = recipe_version_test_execution_qry_srv.get_recipe_version_test_execution(
        version_id=command.recipeVersionId.value, test_execution_id=command.testExecutionId.value
    )
    instance_id = recipe_version_test_execution_entity.instanceId
    command_id = recipe_version_test_execution_entity.testCommandId

    command_status = recipe_version_test_execution_command_status_value_object.from_str(
        recipe_version_testing_srv.get_testing_command_status(command_id=command_id, instance_id=instance_id)
    ).value
    update_attributes = {"testCommandStatus": command_status}

    current_time = datetime.now(timezone.utc).isoformat()
    update_attributes["lastUpdateDate"] = current_time
    match command_status:
        case recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success:
            update_attributes["status"] = recipe_version_test_execution.RecipeVersionTestExecutionStatus.Success.value
        case (
            recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Running
            | recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Pending
        ):
            update_attributes["status"] = recipe_version_test_execution.RecipeVersionTestExecutionStatus.Running.value
        case recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Failed:
            update_attributes["status"] = recipe_version_test_execution.RecipeVersionTestExecutionStatus.Failed.value

    with uow:
        uow.get_repository(
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey,
            recipe_version_test_execution.RecipeVersionTestExecution,
        ).update_attributes(
            recipe_version_test_execution.RecipeVersionTestExecutionPrimaryKey(
                recipeVersionId=command.recipeVersionId.value,
                testExecutionId=command.testExecutionId.value,
            ),
            **update_attributes,
        )
        uow.commit()

    return command_status
