from datetime import datetime, timezone

from app.packaging.domain.commands.recipe import create_recipe_command
from app.packaging.domain.model.recipe import recipe
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: create_recipe_command.CreateRecipeCommand,
    uow: unit_of_work.UnitOfWork,
):
    current_time = datetime.now(timezone.utc).isoformat()

    recipe_entity = recipe.Recipe(
        projectId=command.projectId.value,
        recipeDescription=command.recipeDescription.value,
        recipeName=command.recipeName.value,
        recipePlatform=command.recipeSystemConfiguration.platform,
        recipeArchitecture=command.recipeSystemConfiguration.architecture,
        recipeOsVersion=command.recipeSystemConfiguration.os_version,
        status=recipe.RecipeStatus.Created,
        createDate=current_time,
        lastUpdateDate=current_time,
        createdBy=command.createdBy.value,
        lastUpdatedBy=command.createdBy.value,
    )

    with uow:
        uow.get_repository(repo_key=recipe.RecipePrimaryKey, repo_type=recipe.Recipe).add(recipe_entity)
        uow.commit()
