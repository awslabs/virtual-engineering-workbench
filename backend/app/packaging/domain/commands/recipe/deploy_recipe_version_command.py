from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_components_versions_value_object,
    recipe_version_id_value_object,
    recipe_version_name_value_object,
    recipe_version_parent_image_upstream_id_value_object,
    recipe_version_volume_size_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class DeployRecipeVersionCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    recipeId: recipe_id_value_object.RecipeIdValueObject
    recipeVersionId: recipe_version_id_value_object.RecipeVersionIdValueObject
    components: recipe_version_components_versions_value_object.RecipeVersionComponentsVersionsValueObject
    parentImageUpstreamId: (
        recipe_version_parent_image_upstream_id_value_object.RecipeVersionParentImageUpstreamIdValueObject
    )
    recipeVersionName: recipe_version_name_value_object.RecipeVersionNameValueObject
    recipeVersionVolumeSize: recipe_version_volume_size_value_object.RecipeVersionVolumeSizeValueObject
