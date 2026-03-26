from app.packaging.domain.commands.recipe import update_recipe_version_on_component_update_command
from app.packaging.domain.events.recipe import recipe_version_update_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared import component_version_entry, recipe_version_entry
from app.packaging.domain.ports import (
    component_query_service,
    component_version_query_service,
    recipe_version_query_service,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand,
    component_qry_srv: component_query_service.ComponentQueryService,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
):
    component_version_entity = __get_component_version(command, component_version_qry_srv)

    if component_version_entity.associatedRecipesVersions:
        for recipe in component_version_entity.associatedRecipesVersions:
            __update_recipe_version(
                recipe,
                component_qry_srv,
                recipe_version_query_service,
                component_version_entity,
                uow,
                message_bus,
            )


def __get_component_version(
    command: update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand,
    component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
):
    component_version_entity = component_version_qry_srv.get_component_version(
        command.componentId.value, command.componentVersionId.value
    )
    if not component_version_entity:
        raise domain_exception.DomainException(
            f"Version {command.componentVersionId} of component {command.componentId} does not exist."
        )
    return component_version_entity


def __update_recipe_version(
    recipe: recipe_version_entry.RecipeVersionEntry,
    component_qry_srv: component_query_service.ComponentQueryService,
    recipe_version_query_service: recipe_version_query_service.RecipeVersionQueryService,
    component_version_entity: component_version.ComponentVersion,
    uow: unit_of_work.UnitOfWork,
    message_bus: message_bus.MessageBus,
):
    recipe_version_entity = recipe_version_query_service.get_recipe_version(recipe.recipeId, recipe.recipeVersionId)
    if recipe_version_entity is None:
        raise domain_exception.DomainException(
            f"Version {recipe.recipeVersionId} of recipe {recipe.recipeId} does not exist."
        )

    if recipe_version_entity.recipeComponentsVersions:
        previous_components = recipe_version_entity.recipeComponentsVersions
        if __update_recipe_components(recipe_version_entity, component_version_entity, uow):
            __publish_update_event(
                recipe_version_entity,
                component_qry_srv,
                component_version_entity,
                previous_components,
                message_bus,
            )


def __update_recipe_components(
    recipe_version_entity: recipe_version.RecipeVersion,
    component_version_entity: component_version.ComponentVersion,
    uow: unit_of_work.UnitOfWork,
):
    updated = False
    if recipe_version_entity.recipeComponentsVersions:
        for recipe_component in recipe_version_entity.recipeComponentsVersions:
            if recipe_component.componentVersionId == component_version_entity.componentVersionId:
                if recipe_component.componentVersionName != component_version_entity.componentVersionName:
                    recipe_component.componentVersionName = component_version_entity.componentVersionName
                    with uow:
                        uow.get_repository(
                            recipe_version.RecipeVersionPrimaryKey, recipe_version.RecipeVersion
                        ).update_entity(
                            recipe_version.RecipeVersionPrimaryKey(
                                recipeId=recipe_version_entity.recipeId,
                                recipeVersionId=recipe_version_entity.recipeVersionId,
                            ),
                            recipe_version_entity,
                        )
                        uow.commit()
                    updated = True
    return updated


def __publish_update_event(
    recipe_version_entity: recipe_version.RecipeVersion,
    component_qry_srv: component_query_service.ComponentQueryService,
    component_version_entity: component_version.ComponentVersion,
    previous_components: list[component_version_entry.ComponentVersionEntry],
    message_bus: message_bus.MessageBus,
):
    component_project_associations_entity = component_qry_srv.get_component_project_associations(
        component_version_entity.componentId
    )
    for component_project_association in component_project_associations_entity:
        message_bus.publish(
            recipe_version_update_started.RecipeVersionUpdateStarted(
                project_id=component_project_association.projectId,
                recipe_id=recipe_version_entity.recipeId,
                recipe_version_id=recipe_version_entity.recipeVersionId,
                recipe_components_versions=recipe_version_entity.recipeComponentsVersions,
                recipe_version_description=recipe_version_entity.recipeVersionDescription,
                recipe_version_volume_size=recipe_version_entity.recipeVersionVolumeSize,
                last_updated_by=component_version_entity.lastUpdatedBy,
                parent_image_upstream_id=recipe_version_entity.parentImageUpstreamId,
                recipe_version_name=recipe_version_entity.recipeVersionName,
                previous_recipe_components_versions=previous_components,
            )
        )
