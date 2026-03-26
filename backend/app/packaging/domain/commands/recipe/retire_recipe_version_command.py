from typing import List

from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.shared.adapters.message_bus import command_bus


class RetireRecipeVersionCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    recipeId: recipe_id_value_object.RecipeIdValueObject
    recipeVersionId: recipe_version_id_value_object.RecipeVersionIdValueObject
    userRoles: List[user_role_value_object.UserRoleValueObject]
    lastUpdatedBy: user_id_value_object.UserIdValueObject
