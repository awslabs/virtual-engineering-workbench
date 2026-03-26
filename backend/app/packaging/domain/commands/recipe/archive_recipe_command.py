from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class ArchiveRecipeCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    recipeId: recipe_id_value_object.RecipeIdValueObject
    lastUpdatedBy: user_id_value_object.UserIdValueObject
