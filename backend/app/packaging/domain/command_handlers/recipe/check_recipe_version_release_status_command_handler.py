from app.packaging.domain.commands.recipe import check_recipe_version_release_status_command
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import recipe_version_query_service


def handle(
    command: check_recipe_version_release_status_command.CheckRecipeVersionReleaseStatusCommand,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService,
) -> dict[str, str]:
    recipe_version_obj = recipe_version_query_service.get_recipe_version(
        recipe_id=command.recipeId.value,
        version_id=command.recipeVersionId.value,
    )

    if not recipe_version_obj:
        return {
            "recipeVersionStatus": recipe_version.RecipeVersionStatus.Failed.value,
            "recipeVersionId": command.recipeVersionId.value,
        }

    status = recipe_version_obj.status

    if status == recipe_version.RecipeVersionStatus.Released:
        return {
            "recipeVersionStatus": recipe_version.RecipeVersionStatus.Released.value,
            "recipeVersionId": command.recipeVersionId.value,
        }
    elif status in [recipe_version.RecipeVersionStatus.Failed]:
        return {
            "recipeVersionStatus": recipe_version.RecipeVersionStatus.Failed.value,
            "recipeVersionId": command.recipeVersionId.value,
        }
    else:
        return {
            "recipeVersionStatus": recipe_version.RecipeVersionStatus.Updating.value,
            "recipeVersionId": command.recipeVersionId.value,
        }
