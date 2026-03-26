from datetime import datetime, timezone

from app.packaging.domain.commands.recipe import remove_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_retirement_failed
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import component_version_service, recipe_version_service
from app.shared.adapters.message_bus.message_bus import MessageBus
from app.shared.adapters.unit_of_work_v2.unit_of_work import UnitOfWork


def handle(
    command: remove_recipe_version_command.RemoveRecipeVersionCommand,
    message_bus: MessageBus,
    uow: UnitOfWork,
    component_version_service: component_version_service.ComponentVersionService,
    recipe_version_service: recipe_version_service.RecipeVersionService,
):
    status = recipe_version.RecipeVersionStatus.Retired

    try:
        recipe_version_service.delete(recipe_version_arn=command.recipeVersionArn.value)
        component_version_service.delete(component_build_version_arn=command.recipeVersionComponentArn.value)
    except:
        status = recipe_version.RecipeVersionStatus.Failed

        message_bus.publish(
            recipe_version_retirement_failed.RecipeVersionRetirementFailed(
                projectId=command.projectId.value,
                recipeName=command.recipeName.value,
                recipeVersionName=command.recipeVersionName.value,
                lastUpdatedBy=command.lastUpdatedBy.value,
            )
        )
    finally:
        current_time = datetime.now(timezone.utc).isoformat()

        with uow:
            uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).update_attributes(
                recipe_version.RecipeVersionPrimaryKey(
                    recipeId=command.recipeId.value,
                    recipeVersionId=command.recipeVersionId.value,
                ),
                lastUpdateDate=current_time,
                status=status,
            )
            uow.commit()
