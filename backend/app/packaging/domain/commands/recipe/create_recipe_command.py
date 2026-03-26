from app.packaging.domain.value_objects.recipe import (
    recipe_description_value_object,
    recipe_name_value_object,
    recipe_system_configuration_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class CreateRecipeCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    recipeDescription: recipe_description_value_object.RecipeDescriptionValueObject
    recipeName: recipe_name_value_object.RecipeNameValueObject
    recipeSystemConfiguration: recipe_system_configuration_value_object.RecipeSystemConfigurationValueObject
    createdBy: user_id_value_object.UserIdValueObject
