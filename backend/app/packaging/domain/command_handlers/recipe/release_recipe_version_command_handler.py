from datetime import datetime, timezone

import semver

from app.packaging.domain.commands.recipe import release_recipe_version_command
from app.packaging.domain.events.recipe import recipe_version_release_completed
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import (
    component_version_query_service,
    recipe_version_query_service,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def validate_recipe_version_entity(recipe_version_entity, command):
    if recipe_version_entity is None:
        raise domain_exception.DomainException(
            f"Version {command.recipeVersionId.value} of recipe {command.recipeId.value} does not exist."
        )
    try:
        recipe_version_parsed = semver.Version.parse(recipe_version_entity.recipeVersionName)
    except Exception:
        raise domain_exception.DomainException(
            f"Version {recipe_version_entity.recipeVersionName} is not a valid SemVer string."
        )
    if recipe_version_parsed.prerelease is None:
        raise domain_exception.DomainException(
            f"Cannot release an already released recipe version {recipe_version_entity.recipeVersionName} - Only *rc allowed."
        )
    if recipe_version_entity.status is not recipe_version.RecipeVersionStatus.Validated:
        raise domain_exception.DomainException(
            f"Version {recipe_version_entity.recipeVersionName} of recipe {command.recipeId.value} has not been validated."
        )
    return recipe_version_parsed


def update_component_versions(recipe_version_entity, component_version_qry_srv):
    for component_version_entry in recipe_version_entity.recipeComponentsVersions:
        component_version_entity = component_version_qry_srv.get_component_version(
            component_id=component_version_entry.componentId,
            version_id=component_version_entry.componentVersionId,
        )

        if component_version_entity.status != component_version.ComponentVersionStatus.Released:
            raise domain_exception.DomainException(
                f"Version {component_version_entry.componentVersionId} of component "
                f"{component_version_entry.componentId} has not been released."
            )

        if component_version_entity.componentVersionName != component_version_entry.componentVersionName:
            component_version_entry.componentVersionName = component_version_entity.componentVersionName


def finalize_recipe_version_name(recipe_version_parsed):
    return str(recipe_version_parsed.finalize_version())


def handle(
    command: release_recipe_version_command.ReleaseRecipeVersionCommand,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
):
    recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
        recipe_id=command.recipeId.value, version_id=command.recipeVersionId.value
    )

    # Step 1: Validate the recipe version entity
    recipe_version_parsed = validate_recipe_version_entity(recipe_version_entity, command)

    # Step 2: Update component versions if needed
    update_component_versions(recipe_version_entity, component_version_qry_srv)

    # Step 3: Finalize recipe version name and prepare update attributes
    final_recipe_version_name = finalize_recipe_version_name(recipe_version_parsed)
    current_time = datetime.now(timezone.utc).isoformat()
    recipe_version_entity.lastUpdateDate = current_time
    recipe_version_entity.status = recipe_version.RecipeVersionStatus.Released
    recipe_version_entity.lastUpdatedBy = command.lastUpdatedBy.value
    recipe_version_entity.recipeVersionName = final_recipe_version_name

    # Step 4: Persist the updated recipe version
    with uow:
        uow.get_repository(recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion).update_entity(
            recipe_version.RecipeVersionPrimaryKey(
                recipeId=command.recipeId.value,
                recipeVersionId=command.recipeVersionId.value,
            ),
            recipe_version_entity,
        )
        uow.commit()

    # Step 5: Publish the release completed event
    message_bus.publish(
        recipe_version_release_completed.RecipeVersionReleaseCompleted(
            recipe_id=command.recipeId.value,
            recipe_version_id=command.recipeVersionId.value,
            recipeComponentsVersions=recipe_version_entity.recipeComponentsVersions,
        )
    )

    return {"recipeVersionId": command.recipeVersionId.value}
