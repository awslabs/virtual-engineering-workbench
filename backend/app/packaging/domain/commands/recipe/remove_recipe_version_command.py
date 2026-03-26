from app.packaging.domain.value_objects.component import component_build_version_arn_value_object
from app.packaging.domain.value_objects.recipe import recipe_id_value_object, recipe_name_value_object
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_arn_value_object,
    recipe_version_id_value_object,
    recipe_version_name_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class RemoveRecipeVersionCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    recipeId: recipe_id_value_object.RecipeIdValueObject
    recipeName: recipe_name_value_object.RecipeNameValueObject
    recipeVersionId: recipe_version_id_value_object.RecipeVersionIdValueObject
    recipeVersionArn: recipe_version_arn_value_object.RecipeVersionArnValueObject
    recipeVersionComponentArn: component_build_version_arn_value_object.ComponentBuildVersionArnValueObject
    recipeVersionName: recipe_version_name_value_object.RecipeVersionNameValueObject
    lastUpdatedBy: user_id_value_object.UserIdValueObject
