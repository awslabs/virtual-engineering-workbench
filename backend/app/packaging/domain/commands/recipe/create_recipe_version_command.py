from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_components_versions_value_object,
    recipe_version_description_value_object,
    recipe_version_integration_value_object,
    recipe_version_release_type_value_object,
    recipe_version_volume_size_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class CreateRecipeVersionCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    recipeId: recipe_id_value_object.RecipeIdValueObject
    recipeComponentsVersions: recipe_version_components_versions_value_object.RecipeVersionComponentsVersionsValueObject
    recipeVersionDescription: recipe_version_description_value_object.RecipeVersionDescriptionValueObject
    recipeVersionReleaseType: recipe_version_release_type_value_object.RecipeVersionReleaseTypeValueObject
    recipeVersionVolumeSize: recipe_version_volume_size_value_object.RecipeVersionVolumeSizeValueObject
    recipeVersionIntegrations: list[recipe_version_integration_value_object.RecipeVersionIntegrationValueObject]
    createdBy: user_id_value_object.UserIdValueObject
