import logging
from enum import StrEnum

from app.packaging.domain.commands.recipe import update_recipe_version_associations_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared import component_version_entry, recipe_version_entry
from app.packaging.domain.ports import component_version_query_service, recipe_version_query_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ActionType(StrEnum):
    UPSERT = "upsert"
    DELETE = "delete"


def __get_component_version(
    component_version_qry_svc: component_version_query_service.ComponentVersionQueryService,
    component_id: str,
    component_version_id: str,
    logger: logging.Logger,
) -> component_version.ComponentVersion:
    component_version_entity = component_version_qry_svc.get_component_version(
        component_id=component_id,
        version_id=component_version_id,
    )
    if component_version_entity is None:
        exception_message = f"Version {component_version_id} for {component_id} can not be found."
        logger.exception(exception_message)
        raise domain_exception.DomainException(exception_message)

    return component_version_entity


def __get_recipe_version(
    recipe_version_qry_svc: recipe_version_query_service.RecipeVersionQueryService,
    recipe_id: str,
    recipe_version_id: str,
    logger: logging.Logger,
) -> recipe_version.RecipeVersion:
    recipe_version_entity = recipe_version_qry_svc.get_recipe_version(
        recipe_id=recipe_id,
        version_id=recipe_version_id,
    )
    if recipe_version_entity is None:
        exception_message = f"Version {recipe_id} of recipe {recipe_version_id} can not be found."
        logger.exception(exception_message)
        raise domain_exception.DomainException(exception_message)
    return recipe_version_entity


def __validate_recipe_version_status(
    recipe_version_entity: recipe_version.RecipeVersion,
    logger: logging.Logger,
):
    valid_status = [
        recipe_version.RecipeVersionStatus.Created.value,
        recipe_version.RecipeVersionStatus.Released.value,
        recipe_version.RecipeVersionStatus.Retired.value,
        recipe_version.RecipeVersionStatus.Validated.value,
    ]
    if recipe_version_entity.status not in valid_status:
        exception_message = (
            f"Version {recipe_version_entity.recipeVersionName} of "
            f"recipe {recipe_version_entity.recipeId} "
            f"can't be associated while in {recipe_version_entity.status} status: "
            f"only {recipe_version.RecipeVersionStatus.Created}, "
            f"{recipe_version.RecipeVersionStatus.Released}, "
            f"{recipe_version.RecipeVersionStatus.Retired} and "
            f"{recipe_version.RecipeVersionStatus.Validated} states are accepted."
        )
        logger.exception(exception_message)
        raise domain_exception.DomainException(exception_message)


def __validate_component_version_status(
    component_version_entity: component_version.ComponentVersion,
    logger: logging.Logger,
) -> bool:
    valid_status = [
        component_version.ComponentVersionStatus.Released.value,
        component_version.ComponentVersionStatus.Validated.value,
    ]
    if component_version_entity.status not in valid_status:
        exception_message = (
            f"Version {component_version_entity.componentVersionName} of "
            f"component {component_version_entity.componentId} "
            f"can't be associated while in {component_version_entity.status} status: "
            f"only {component_version.ComponentVersionStatus.Released} and "
            f"{component_version.ComponentVersionStatus.Validated} states are accepted."
        )
        logger.exception(exception_message)
        raise domain_exception.DomainException(exception_message)


def __update_associated_recipes_versions_list(
    uow: unit_of_work.UnitOfWork,
    component_version_qry_svc: component_version_query_service.ComponentVersionQueryService,
    components_versions_list: list[component_version_entry.ComponentVersionEntry],
    recipe_version_entity: recipe_version.RecipeVersion,
    action_type: ActionType,
    logger: logging.Logger,
):

    for component_version_entry_obj in components_versions_list:
        component_version_entity: component_version.ComponentVersion = __get_component_version(
            component_version_qry_svc=component_version_qry_svc,
            component_id=component_version_entry_obj.componentId,
            component_version_id=component_version_entry_obj.componentVersionId,
            logger=logger,
        )

        __validate_component_version_status(component_version_entity=component_version_entity, logger=logger)

        match action_type:
            case ActionType.UPSERT:
                if not component_version_entity.associatedRecipesVersions:
                    component_version_entity.associatedRecipesVersions = list()

                # This covers cases when the recipe version name changes but
                # everything else stays the same (i.e. recipe version release)
                match_found = False
                for i, associated_recipe_version in enumerate(component_version_entity.associatedRecipesVersions):
                    if (
                        associated_recipe_version.recipeId == recipe_version_entity.recipeId
                        and associated_recipe_version.recipeName == recipe_version_entity.recipeName
                        and associated_recipe_version.recipeVersionId == recipe_version_entity.recipeVersionId
                        and associated_recipe_version.recipeVersionName != recipe_version_entity.recipeVersionName
                    ):
                        match_found = True
                        component_version_entity.associatedRecipesVersions[i].recipeVersionName = (
                            recipe_version_entity.recipeVersionName
                        )

                if not match_found:
                    component_version_entity.associatedRecipesVersions.append(
                        recipe_version_entry.RecipeVersionEntry(
                            recipeId=recipe_version_entity.recipeId,
                            recipeName=recipe_version_entity.recipeName,
                            recipeVersionId=recipe_version_entity.recipeVersionId,
                            recipeVersionName=recipe_version_entity.recipeVersionName,
                        )
                    )
            case ActionType.DELETE:
                component_version_entity.associatedRecipesVersions = [
                    recipe_version_associated_entity
                    for recipe_version_associated_entity in component_version_entity.associatedRecipesVersions
                    if recipe_version_associated_entity.recipeId != recipe_version_entity.recipeId
                    and recipe_version_associated_entity.recipeVersionId
                    != recipe_version_associated_entity.recipeVersionId
                ]
            case _:
                logger.exception(f"Invalid action type {action_type}.")
                raise domain_exception.DomainException(f"Invalid action type {action_type}.")

        with uow:
            uow.get_repository(
                component_version.ComponentVersionPrimaryKey, component_version.ComponentVersion
            ).update_entity(
                component_version.ComponentVersionPrimaryKey(
                    componentId=component_version_entity.componentId,
                    componentVersionId=component_version_entity.componentVersionId,
                ),
                component_version_entity,
            )
            uow.commit()


def handle(
    command: update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand,
    recipe_version_qry_svc: recipe_version_query_service.RecipeVersionQueryService,
    component_version_qry_svc: component_version_query_service.ComponentVersionQueryService,
    logger: logging.Logger,
    uow: unit_of_work.UnitOfWork,
):
    recipe_version_entity: recipe_version.RecipeVersion = __get_recipe_version(
        recipe_version_qry_svc=recipe_version_qry_svc,
        recipe_id=command.recipeId.value,
        recipe_version_id=command.recipeVersionId.value,
        logger=logger,
    )

    # Do not perform any action if recipe version status is FAILED
    if recipe_version_entity.status == recipe_version.RecipeVersionStatus.Failed.value:
        logger.info(
            f"Version {recipe_version_entity.recipeVersionName} of "
            f"recipe {recipe_version_entity.recipeId} "
            f"is in {recipe_version_entity.status} status, skipping."
        )
        return
    __validate_recipe_version_status(recipe_version_entity=recipe_version_entity, logger=logger)
    __update_associated_recipes_versions_list(
        uow=uow,
        component_version_qry_svc=component_version_qry_svc,
        components_versions_list=command.componentsVersionsList.value,
        recipe_version_entity=recipe_version_entity,
        action_type=ActionType.UPSERT,
        logger=logger,
    )

    if command.previousComponentsVersionsList:
        # Remove the current recipe reference from components versions that are
        # only in the previous components versions list
        components_versions_associations_delete = [
            component_version_entry
            for component_version_entry in command.previousComponentsVersionsList.value
            if component_version_entry not in command.componentsVersionsList.value
        ]
        __update_associated_recipes_versions_list(
            uow=uow,
            component_version_qry_svc=component_version_qry_svc,
            components_versions_list=components_versions_associations_delete,
            recipe_version_entity=recipe_version_entity,
            action_type=ActionType.DELETE,
            logger=logger,
        )
