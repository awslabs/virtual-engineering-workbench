from datetime import datetime, timezone

import semver

from app.packaging.domain.commands.recipe import retire_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_retirement_started
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import recipe_version_query_service
from app.shared.adapters.message_bus.message_bus import MessageBus
from app.shared.adapters.unit_of_work_v2.unit_of_work import UnitOfWork
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def handle(
    command: retire_recipe_version_command.RetireRecipeVersionCommand,
    uow: UnitOfWork,
    message_bus: MessageBus,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService,
):
    recipe_version_entity = recipe_version_query_service.get_recipe_version(
        recipe_id=command.recipeId.value, version_id=command.recipeVersionId.value
    )

    if recipe_version_entity is None:
        raise DomainException(
            f"Version {command.recipeVersionId.value} of recipe {command.recipeId.value} can't be found."
        )

    try:
        recipe_version_name = recipe_version_entity.recipeVersionName
        recipe_version_parsed = semver.Version.parse(recipe_version_name)
    except:
        raise DomainException(f"Version {recipe_version_name} is not a valid SemVer string.")

    acceptable_states_for_retirement = [
        recipe_version.RecipeVersionStatus.Failed,
        recipe_version.RecipeVersionStatus.Released,
        recipe_version.RecipeVersionStatus.Validated,
    ]
    acceptable_roles_for_released_retirement = [
        VirtualWorkbenchRoles.Admin,
        VirtualWorkbenchRoles.ProgramOwner,
        VirtualWorkbenchRoles.PowerUser,
    ]

    if recipe_version_entity.status not in acceptable_states_for_retirement:
        raise DomainException(
            f"Version {command.recipeVersionId.value} of recipe {command.recipeId.value} can't be retired while in {recipe_version_entity.status} status."
        )
    if (
        not any([item.value in acceptable_roles_for_released_retirement for item in command.userRoles])
        and recipe_version_parsed.prerelease is None
    ):
        raise DomainException(f"Version {recipe_version_name} of recipe {command.recipeId.value} has been released.")

    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).update_attributes(
            recipe_version.RecipeVersionPrimaryKey(
                recipeId=command.recipeId.value,
                recipeVersionId=command.recipeVersionId.value,
            ),
            lastUpdateDate=current_time,
            lastUpdateBy=command.lastUpdatedBy.value,
            status=recipe_version.RecipeVersionStatus.Updating,
        )
        uow.commit()

    message_bus.publish(
        recipe_version_retirement_started.RecipeVersionRetirementStarted(
            projectId=command.projectId.value,
            recipeId=command.recipeId.value,
            recipeName=recipe_version_entity.recipeName,
            recipeVersionId=command.recipeVersionId.value,
            recipeVersionArn=recipe_version_entity.recipeVersionArn,
            recipeVersionComponentArn=recipe_version_entity.recipeVersionComponentArn,
            recipeVersionName=recipe_version_entity.recipeVersionName,
            recipeComponentsVersions=recipe_version_entity.recipeComponentsVersions,
            lastUpdatedBy=command.lastUpdatedBy.value,
        )
    )
