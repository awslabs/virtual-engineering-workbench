from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.message_bus import command_bus


class ReleaseRecipeVersionCommand(command_bus.Command):
    recipeId: recipe_id_value_object.RecipeIdValueObject
    recipeVersionId: recipe_version_id_value_object.RecipeVersionIdValueObject
    lastUpdatedBy: user_id_value_object.UserIdValueObject
