from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class CheckRecipeVersionTestingEnvironmentLaunchStatusCommand(command_bus.Command):
    recipeVersionId: recipe_version_id_value_object.RecipeVersionIdValueObject
    testExecutionId: recipe_version_test_execution_id_value_object.RecipeVersionTestExecutionIdValueObject
