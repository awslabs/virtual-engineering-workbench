from app.packaging.domain.commands.recipe import complete_recipe_version_testing_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe_version, recipe_version_test_execution
from app.packaging.domain.ports import (
    recipe_query_service,
    recipe_version_test_execution_query_service,
    recipe_version_testing_service,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: complete_recipe_version_testing_command.CompleteRecipeVersionTestingCommand,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    recipe_version_test_execution_qry_srv: recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService,
    recipe_version_testing_srv: recipe_version_testing_service.RecipeVersionTestingService,
    uow: unit_of_work.UnitOfWork,
):
    recipe_entity = recipe_qry_srv.get_recipe(project_id=command.projectId.value, recipe_id=command.recipeId.value)

    if recipe_entity is None:
        raise domain_exception.DomainException(f"Recipe {command.recipeId.value} does not exist.")

    recipe_version_test_execution_entity = recipe_version_test_execution_qry_srv.get_recipe_version_test_execution(
        version_id=command.recipeVersionId.value, test_execution_id=command.testExecutionId.value
    )
    instance_id = recipe_version_test_execution_entity.instanceId
    test_status = (
        recipe_version_test_execution.RecipeVersionTestExecutionStatus.Success
        if recipe_version_test_execution_entity.testCommandStatus
        == recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success
        else recipe_version_test_execution.RecipeVersionTestExecutionStatus.Failed
    )

    # First we teardown the testing environment
    recipe_version_testing_srv.teardown_testing_environment(instance_id=instance_id)

    # Finally we update the recipe version status
    with uow:
        uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).update_attributes(
            recipe_version.RecipeVersionPrimaryKey(
                recipeId=command.recipeId.value,
                recipeVersionId=command.recipeVersionId.value,
            ),
            status=(
                recipe_version.RecipeVersionStatus.Validated
                if test_status == recipe_version_test_execution.RecipeVersionTestExecutionStatus.Success
                else recipe_version.RecipeVersionStatus.Failed
            ),
        )
        uow.commit()

    return test_status
