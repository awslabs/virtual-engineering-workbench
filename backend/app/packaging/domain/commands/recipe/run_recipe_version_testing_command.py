from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.recipe_version_test_execution import (
    recipe_version_test_execution_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class RunRecipeVersionTestingCommand(command_bus.Command):
    recipeId: recipe_id_value_object.RecipeIdValueObject
    recipeVersionId: recipe_version_id_value_object.RecipeVersionIdValueObject
    testExecutionId: recipe_version_test_execution_id_value_object.RecipeVersionTestExecutionIdValueObject
