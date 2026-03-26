from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
)
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_release_type_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class CreateAutomatedRecipeVersionCommand(command_bus.Command):
    recipeId: recipe_id_value_object.RecipeIdValueObject
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionId: component_version_id_value_object.ComponentVersionIdValueObject
    projectId: project_id_value_object.ProjectIdValueObject
    recipeVersionReleaseType: recipe_version_release_type_value_object.RecipeVersionReleaseTypeValueObject
    createdBy: user_id_value_object.UserIdValueObject
