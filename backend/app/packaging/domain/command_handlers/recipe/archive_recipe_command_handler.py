from datetime import datetime, timezone

from app.packaging.domain.commands.recipe import archive_recipe_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe, recipe_version
from app.packaging.domain.ports import recipe_query_service, recipe_version_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: archive_recipe_command.ArchiveRecipeCommand,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    uow: unit_of_work.UnitOfWork,
):
    recipe_entity = recipe_qry_srv.get_recipe(command.projectId.value, command.recipeId.value)

    if recipe_entity is None:
        raise domain_exception.DomainException(f"Recipe {command.recipeId.value} can not be found.")

    recipe_versions_entities = recipe_version_qry_srv.get_recipe_versions(recipe_id=command.recipeId.value)

    for recipe_version_entity in recipe_versions_entities:
        if recipe_version_entity.status is not recipe_version.RecipeVersionStatus.Retired:
            raise domain_exception.DomainException(
                f"Recipe {command.recipeId.value} cannot be retired because recipe version "
                f"{recipe_version_entity.recipeVersionId} is in {recipe_version_entity.status} status."
            )

    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(recipe.RecipePrimaryKey, recipe.Recipe).update_attributes(
            recipe.RecipePrimaryKey(
                projectId=command.projectId.value,
                recipeId=command.recipeId.value,
            ),
            lastUpdateBy=command.lastUpdatedBy.value,
            lastUpdateDate=current_time,
            status=recipe.RecipeStatus.Archived,
        )
        uow.commit()
