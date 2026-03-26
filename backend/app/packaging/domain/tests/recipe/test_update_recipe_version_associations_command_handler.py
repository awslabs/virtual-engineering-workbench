import logging
from unittest import mock

import assertpy
import pytest

from app.packaging.domain.command_handlers.recipe import update_recipe_version_associations_command_handler
from app.packaging.domain.commands.recipe.update_recipe_version_associations_command import (
    UpdateRecipeVersionAssociationsCommand,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.model.shared import component_version_entry, recipe_version_entry
from app.packaging.domain.value_objects.component_version import components_versions_list_value_object
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def update_recipe_version_associations_command_mock() -> UpdateRecipeVersionAssociationsCommand:
    return UpdateRecipeVersionAssociationsCommand(
        recipeId=recipe_id_value_object.from_str("reci-1234abcd"),
        recipeVersionId=recipe_version_id_value_object.from_str("vers-1234abcd"),
        componentsVersionsList=components_versions_list_value_object.from_list([]),
    )


@pytest.fixture()
def get_component_for_recipe_association_test():
    def _get_test_component_version_with_specific_component_id_version_name_and_status_ans_associations(
        get_test_component_id,
        get_test_component_version_id,
        get_test_component_version_arn,
        get_test_architecture,
        get_test_os_version,
        version_name,
        get_test_platform,
        associated_recipe_versions: list[recipe_version_entry.RecipeVersionEntry],
        status: component_version.ComponentVersionStatus = component_version.ComponentVersionStatus.Created,
    ):
        if associated_recipe_versions is None:
            associated_recipe_versions = []
        if not version_name:
            return None
        return component_version.ComponentVersion(
            componentId=get_test_component_id,
            componentVersionId=get_test_component_version_id,
            componentVersionName=version_name,
            componentName="test-component",
            componentVersionDescription="Test description",
            componentBuildVersionArn=get_test_component_version_arn(version_name),
            associatedRecipesVersions=associated_recipe_versions,
            componentVersionS3Uri="s3://test/component.yaml",
            componentPlatform=get_test_platform,
            componentSupportedArchitectures=[get_test_architecture],
            componentSupportedOsVersions=[get_test_os_version],
            softwareVendor="vector",
            softwareVersion="1.0.0",
            status=status,
            createDate="2023-10-27T00:00:00+00:00",
            createdBy="T000001",
            lastUpdateDate="2023-10-27T00:00:00+00:00",
            lastUpdatedBy="T000001",
        )

    return _get_test_component_version_with_specific_component_id_version_name_and_status_ans_associations


@pytest.mark.parametrize("version", ("1.0.0", "1.0.0-rc1", "1.3.0"))
def test_get_recipe_version_should_return_recipe_entity(
    get_test_recipe_version_with_specific_version_name,
    recipe_version_query_service_mock,
    get_test_recipe_id,
    get_test_recipe_version_id,
    version,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = (
        get_test_recipe_version_with_specific_version_name(version)
    )

    # ACT
    recipe_version_entity = update_recipe_version_associations_command_handler.__get_recipe_version(
        recipe_version_qry_svc=recipe_version_query_service_mock,
        recipe_id=get_test_recipe_id,
        recipe_version_id=get_test_recipe_version_id,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    assertpy.assert_that(recipe_version_entity).is_equal_to(get_test_recipe_version_with_specific_version_name(version))


def test_get_recipe_version_should_raise_if_not_found(
    recipe_version_query_service_mock,
    get_test_recipe_id,
    get_test_recipe_version_id,
):
    # ARRANGE
    recipe_version_query_service_mock.get_recipe_version.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_recipe_version_associations_command_handler.__get_recipe_version(
            recipe_version_qry_svc=recipe_version_query_service_mock,
            recipe_id=get_test_recipe_id,
            recipe_version_id=get_test_recipe_version_id,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {get_test_recipe_id} of recipe {get_test_recipe_version_id} can not be found."
    )


def test_get_component_version_should_return_component_entity(
    component_version_query_service_mock,
    get_test_component_version,
    get_test_component_id,
    get_test_component_version_id,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = get_test_component_version

    # ACT
    component_version_entity = update_recipe_version_associations_command_handler.__get_component_version(
        component_version_qry_svc=component_version_query_service_mock,
        component_id=get_test_component_id,
        component_version_id=get_test_component_version_id,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    assertpy.assert_that(component_version_entity).is_equal_to(get_test_component_version)


def test_get_component_version_should_raise_if_not_found(
    component_version_query_service_mock,
    get_test_component_id,
    get_test_component_version_id,
):
    # ARRANGE
    component_version_query_service_mock.get_component_version.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_recipe_version_associations_command_handler.__get_component_version(
            component_version_qry_svc=component_version_query_service_mock,
            component_id=get_test_component_id,
            component_version_id=get_test_component_version_id,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Version {get_test_component_version_id} for {get_test_component_id} can not be found."
    )


def test_update_associated_recipes_versions_list_should_add_to_list(
    component_version_query_service_mock,
    get_test_component_version_with_specific_version_name_and_status,
    get_test_recipe_version_with_specific_version_name,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    component_version_entity: component_version.ComponentVersion = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name="1.0.0",
            status=component_version.ComponentVersionStatus.Released,
        )
    )
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name("1.0.0")
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    components_versions_list = [
        component_version_entry.ComponentVersionEntry(
            componentId=component_version_entity.componentId,
            componentName=component_version_entity.componentName,
            componentVersionId=component_version_entity.componentVersionId,
            componentVersionName=component_version_entity.componentVersionName,
        )
    ]
    component_version_entity.associatedRecipesVersions = list()

    # ACT
    update_recipe_version_associations_command_handler.__update_associated_recipes_versions_list(
        uow=uow_mock,
        component_version_qry_svc=component_version_query_service_mock,
        components_versions_list=components_versions_list,
        recipe_version_entity=recipe_version_entity,
        action_type=update_recipe_version_associations_command_handler.ActionType.UPSERT,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    component_version_entity.associatedRecipesVersions.append(
        recipe_version_entry.RecipeVersionEntry(
            recipeId=recipe_version_entity.recipeId,
            recipeName=recipe_version_entity.recipeName,
            recipeVersionId=recipe_version_entity.recipeVersionId,
            recipeVersionName=recipe_version_entity.recipeVersionName,
        )
    )

    # ASSERT
    component_version_repo_mock.update_entity.assert_any_call(
        component_version.ComponentVersionPrimaryKey(
            componentId=component_version_entity.componentId,
            componentVersionId=component_version_entity.componentVersionId,
        ),
        component_version_entity,
    )
    uow_mock.commit.assert_called()


def test_update_associated_recipes_versions_list_should_delete_from_list(
    component_version_query_service_mock,
    get_test_component_version_with_specific_version_name_and_status,
    get_test_recipe_version_with_specific_version_name,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    component_version_entity: component_version.ComponentVersion = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name="1.0.0",
            status=component_version.ComponentVersionStatus.Released,
        )
    )
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name("1.0.0")
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    components_versions_list = [
        component_version_entry.ComponentVersionEntry(
            componentId=component_version_entity.componentId,
            componentName=component_version_entity.componentName,
            componentVersionId=component_version_entity.componentVersionId,
            componentVersionName=component_version_entity.componentVersionName,
        )
    ]
    component_version_entity.associatedRecipesVersions = [
        recipe_version_entry.RecipeVersionEntry(
            recipeId=recipe_version_entity.recipeId,
            recipeName=recipe_version_entity.recipeName,
            recipeVersionId=recipe_version_entity.recipeVersionId,
            recipeVersionName=recipe_version_entity.recipeVersionName,
        ),
        recipe_version_entry.RecipeVersionEntry(
            recipeId="reci-1234",
            recipeName="test-recipe",
            recipeVersionId="vers-1234",
            recipeVersionName="1.0.0",
        ),
    ]

    # ACT
    update_recipe_version_associations_command_handler.__update_associated_recipes_versions_list(
        uow=uow_mock,
        component_version_qry_svc=component_version_query_service_mock,
        components_versions_list=components_versions_list,
        recipe_version_entity=recipe_version_entity,
        action_type=update_recipe_version_associations_command_handler.ActionType.DELETE,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    component_version_repo_mock.update_entity.assert_any_call(
        component_version.ComponentVersionPrimaryKey(
            componentId=component_version_entity.componentId,
            componentVersionId=component_version_entity.componentVersionId,
        ),
        component_version_entity,
    )
    uow_mock.commit.assert_called()


def test_update_associated_recipes_versions_list_should_raise_if_invalid_action(
    component_version_query_service_mock,
    get_test_component_version_with_specific_version_name_and_status,
    get_test_recipe_version_with_specific_version_name,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {component_version.ComponentVersion: component_version_repo_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    component_version_entity: component_version.ComponentVersion = (
        get_test_component_version_with_specific_version_name_and_status(
            version_name="1.0.0", status=component_version.ComponentVersionStatus.Released
        )
    )
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name("1.0.0")
    component_version_query_service_mock.get_component_version.return_value = component_version_entity
    components_versions_list = [
        component_version_entry.ComponentVersionEntry(
            componentId=component_version_entity.componentId,
            componentName=component_version_entity.componentName,
            componentVersionId=component_version_entity.componentVersionId,
            componentVersionName=component_version_entity.componentVersionName,
        )
    ]

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_recipe_version_associations_command_handler.__update_associated_recipes_versions_list(
            uow=uow_mock,
            component_version_qry_svc=component_version_query_service_mock,
            components_versions_list=components_versions_list,
            recipe_version_entity=recipe_version_entity,
            action_type="INVALID",
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to("Invalid action type INVALID.")


@pytest.mark.parametrize(
    "status",
    (
        recipe_version.RecipeVersionStatus.Failed,
        recipe_version.RecipeVersionStatus.Creating,
        recipe_version.RecipeVersionStatus.Testing,
        recipe_version.RecipeVersionStatus.Updating,
    ),
)
def test_validate_recipe_version_status_should_raise_if_invalid_status(
    get_test_recipe_version_with_specific_version_name_and_status, status
):
    # ARRANGE
    recipe_version_entity = get_test_recipe_version_with_specific_version_name_and_status(
        version_name="1.0.0",
        status=status,
    )
    exception_message = (
        f"Version {recipe_version_entity.recipeVersionName} of "
        f"recipe {recipe_version_entity.recipeId} "
        f"can't be associated while in {recipe_version_entity.status} status: "
        f"only {recipe_version.RecipeVersionStatus.Created}, "
        f"{recipe_version.RecipeVersionStatus.Released}, "
        f"{recipe_version.RecipeVersionStatus.Retired} and "
        f"{recipe_version.RecipeVersionStatus.Validated} states are accepted."
    )

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        update_recipe_version_associations_command_handler.__validate_recipe_version_status(
            recipe_version_entity=recipe_version_entity,
            logger=mock.create_autospec(spec=logging.Logger),
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(exception_message)


@pytest.mark.parametrize(
    "previous_components_versions_list, current_components_versions_list, components_versions_associations_delete_list",
    (
        # Add first component version to a recipe
        (
            [],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                )
            ],
            [],
        ),
        # Add component version to a recipe with already one component version
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                )
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-5678",
                    componentName="component-5678",
                    componentVersionId="vers-5678",
                    componentVersionName="1.0.0",
                ),
            ],
            [],
        ),
        # Bump a component version in a recipe with two components versions (in place update)
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-5678",
                    componentName="component-5678",
                    componentVersionId="vers-5678",
                    componentVersionName="1.0.0",
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-5678",
                    componentName="component-5678",
                    componentVersionId="vers-5678abcd",
                    componentVersionName="1.0.1",
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-5678",
                    componentName="component-5678",
                    componentVersionId="vers-5678",
                    componentVersionName="1.0.0",
                ),
            ],
        ),
        # Remove a component version from a recipe with two components versions
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-5678",
                    componentName="component-5678",
                    componentVersionId="vers-5678",
                    componentVersionName="1.0.0",
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                ),
            ],
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-5678",
                    componentName="component-5678",
                    componentVersionId="vers-5678",
                    componentVersionName="1.0.0",
                ),
            ],
        ),
    ),
)
def test_update_recipe_version_associations_should_pass_when_recipe_version_created_or_updated(
    get_test_recipe_version_with_specific_version_name_and_status,
    get_test_component_version_with_specific_component_id_version_name_and_status,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    update_recipe_version_associations_command_mock,
    previous_components_versions_list,
    current_components_versions_list,
    components_versions_associations_delete_list,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {
        recipe_version.RecipeVersion: recipe_version_repo_mock,
        component_version.ComponentVersion: component_version_repo_mock,
    }
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name_and_status(
        version_name="1.0.0-rc.1",
        status=recipe_version.RecipeVersionStatus.Created,
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    components_versions_associations_delete_entities = list()
    for component_version_entry_obj in components_versions_associations_delete_list:
        component_version_entity_to_delete: component_version.ComponentVersion = (
            get_test_component_version_with_specific_component_id_version_name_and_status(
                component_id=component_version_entry_obj.componentId,
                component_version_id=component_version_entry_obj.componentVersionId,
                version_name=component_version_entry_obj.componentVersionName,
                status=component_version.ComponentVersionStatus.Validated,
            )
        )
        component_version_entity_to_delete.associatedRecipesVersions = [
            recipe_version_entry.RecipeVersionEntry(
                recipeId=recipe_version_entity.recipeId,
                recipeName=recipe_version_entity.recipeName,
                recipeVersionId=recipe_version_entity.recipeVersionId,
                recipeVersionName=recipe_version_entity.recipeVersionName,
            )
        ]
        components_versions_associations_delete_entities.append(component_version_entity_to_delete)

    components_versions_associations_add_entities = list()
    for component_version_entry_obj in current_components_versions_list:
        components_versions_associations_add_entities.append(
            get_test_component_version_with_specific_component_id_version_name_and_status(
                component_id=component_version_entry_obj.componentId,
                component_version_id=component_version_entry_obj.componentVersionId,
                version_name=component_version_entry_obj.componentVersionName,
                status=component_version.ComponentVersionStatus.Validated,
            )
        )

    component_version_query_service_mock.get_component_version.side_effect = (
        components_versions_associations_add_entities + components_versions_associations_delete_entities
    )

    update_recipe_version_associations_command_mock.componentsVersionsList = (
        components_versions_list_value_object.from_list(current_components_versions_list)
    )
    # This is to mimic when the previous components versions list is not in the command (e.g. when a recipe version is created)
    update_recipe_version_associations_command_mock.previousComponentsVersionsList = (
        (components_versions_list_value_object.from_list(previous_components_versions_list))
        if len(previous_components_versions_list) > 0
        else None
    )

    # ACT
    update_recipe_version_associations_command_handler.handle(
        command=update_recipe_version_associations_command_mock,
        uow=uow_mock,
        component_version_qry_svc=component_version_query_service_mock,
        recipe_version_qry_svc=recipe_version_query_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    for component_version_entity in components_versions_associations_add_entities:
        if not component_version_entity.associatedRecipesVersions:
            component_version_entity.associatedRecipesVersions = list()
        component_version_entity.associatedRecipesVersions.append(
            recipe_version_entry.RecipeVersionEntry(
                recipeId=recipe_version_entity.recipeId,
                recipeName=recipe_version_entity.recipeName,
                recipeVersionId=recipe_version_entity.recipeVersionId,
                recipeVersionName=recipe_version_entity.recipeVersionName,
            )
        )
        component_version_repo_mock.update_entity.assert_any_call(
            component_version.ComponentVersionPrimaryKey(
                componentId=component_version_entity.componentId,
                componentVersionId=component_version_entity.componentVersionId,
            ),
            component_version_entity,
        )
        uow_mock.commit.assert_called()

    for component_version_entity in components_versions_associations_delete_entities:
        component_version_entity.associatedRecipesVersions = [
            recipe_version_entry_obj
            for recipe_version_entry_obj in component_version_entity.associatedRecipesVersions
            if recipe_version_entry_obj.recipeId != recipe_version_entity.recipeId
        ]
        component_version_repo_mock.update_entity.assert_any_call(
            component_version.ComponentVersionPrimaryKey(
                componentId=component_version_entity.componentId,
                componentVersionId=component_version_entity.componentVersionId,
            ),
            component_version_entity,
        )
        uow_mock.commit.assert_called()


@pytest.mark.parametrize(
    "current_components_versions_list",
    (
        # Nothing changes during a recipe version release
        (
            [
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-1234",
                    componentName="component-1234",
                    componentVersionId="vers-1234",
                    componentVersionName="1.0.0",
                ),
                component_version_entry.ComponentVersionEntry(
                    componentId="comp-5678",
                    componentName="component-5678",
                    componentVersionId="vers-5678",
                    componentVersionName="1.0.0",
                ),
            ]
        ),
    ),
)
def test_update_recipe_version_associations_should_pass_when_recipe_version_released(
    get_test_recipe_version_with_specific_version_name_and_status,
    get_test_component_version_with_specific_component_id_version_name_and_status,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    update_recipe_version_associations_command_mock,
    current_components_versions_list,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {
        recipe_version.RecipeVersion: recipe_version_repo_mock,
        component_version.ComponentVersion: component_version_repo_mock,
    }
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name_and_status(
        version_name="1.0.0",
        status=recipe_version.RecipeVersionStatus.Released,
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    components_versions_entities = list()
    for component_version_entry_obj in current_components_versions_list:
        component_version_entity: component_version.ComponentVersion = (
            get_test_component_version_with_specific_component_id_version_name_and_status(
                component_id=component_version_entry_obj.componentId,
                component_version_id=component_version_entry_obj.componentVersionId,
                version_name=component_version_entry_obj.componentVersionName,
                status=component_version.ComponentVersionStatus.Released,
            )
        )
        component_version_entity.associatedRecipesVersions = list()
        component_version_entity.associatedRecipesVersions.append(
            recipe_version_entry.RecipeVersionEntry(
                recipeId=recipe_version_entity.recipeId,
                recipeName=recipe_version_entity.recipeName,
                recipeVersionId=recipe_version_entity.recipeVersionId,
                # The component version still points to the RC version at this stage
                recipeVersionName="1.0.0-rc.1",
            )
        )
        components_versions_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = components_versions_entities

    update_recipe_version_associations_command_mock.componentsVersionsList = (
        components_versions_list_value_object.from_list(current_components_versions_list)
    )
    # During a release, the previous components versions list is not passed
    update_recipe_version_associations_command_mock.previousComponentsVersionsList = None

    # ACT
    update_recipe_version_associations_command_handler.handle(
        command=update_recipe_version_associations_command_mock,
        uow=uow_mock,
        component_version_qry_svc=component_version_query_service_mock,
        recipe_version_qry_svc=recipe_version_query_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    for component_version_entity in components_versions_entities:
        for i, _ in enumerate(component_version_entity.associatedRecipesVersions):
            # Point to the recipe final version
            component_version_entity.associatedRecipesVersions[i].recipeVersionName = (
                recipe_version_entity.recipeVersionName
            )

        component_version_repo_mock.update_entity.assert_any_call(
            component_version.ComponentVersionPrimaryKey(
                componentId=component_version_entity.componentId,
                componentVersionId=component_version_entity.componentVersionId,
            ),
            component_version_entity,
        )
        uow_mock.commit.assert_called()


def test_update_recipe_version_associations_should_not_perform_any_action_when_recipe_version_status_is_failed(
    get_test_recipe_version_with_specific_version_name_and_status,
    get_test_component_version_with_specific_component_id_version_name_and_status,
    component_version_query_service_mock,
    recipe_version_query_service_mock,
    update_recipe_version_associations_command_mock,
):
    # ARRANGE
    component_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_repo_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    repos_dict = {
        recipe_version.RecipeVersion: recipe_version_repo_mock,
        component_version.ComponentVersion: component_version_repo_mock,
    }
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda _, x: repos_dict.get(x)
    recipe_version_entity: recipe_version.RecipeVersion = get_test_recipe_version_with_specific_version_name_and_status(
        version_name="1.0.0",
        status=recipe_version.RecipeVersionStatus.Failed,
    )
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_entity

    current_components_versions_list = [
        component_version_entry.ComponentVersionEntry(
            componentId="comp-1234",
            componentName="component-1234",
            componentVersionId="vers-1234",
            componentVersionName="1.0.0",
        ),
        component_version_entry.ComponentVersionEntry(
            componentId="comp-5678",
            componentName="component-5678",
            componentVersionId="vers-5678",
            componentVersionName="1.0.0",
        ),
    ]
    components_versions_entities = list()
    for component_version_entry_obj in current_components_versions_list:
        component_version_entity: component_version.ComponentVersion = (
            get_test_component_version_with_specific_component_id_version_name_and_status(
                component_id=component_version_entry_obj.componentId,
                component_version_id=component_version_entry_obj.componentVersionId,
                version_name=component_version_entry_obj.componentVersionName,
                status=component_version.ComponentVersionStatus.Released,
            )
        )
        component_version_entity.associatedRecipesVersions = list()
        component_version_entity.associatedRecipesVersions.append(
            recipe_version_entry.RecipeVersionEntry(
                recipeId=recipe_version_entity.recipeId,
                recipeName=recipe_version_entity.recipeName,
                recipeVersionId=recipe_version_entity.recipeVersionId,
                recipeVersionName="1.0.0-rc.1",
            )
        )
        components_versions_entities.append(component_version_entity)

    component_version_query_service_mock.get_component_version.side_effect = components_versions_entities

    update_recipe_version_associations_command_mock.componentsVersionsList = (
        components_versions_list_value_object.from_list(current_components_versions_list)
    )
    update_recipe_version_associations_command_mock.previousComponentsVersionsList = None

    # ACT
    update_recipe_version_associations_command_handler.handle(
        command=update_recipe_version_associations_command_mock,
        uow=uow_mock,
        component_version_qry_svc=component_version_query_service_mock,
        recipe_version_qry_svc=recipe_version_query_service_mock,
        logger=mock.create_autospec(spec=logging.Logger),
    )

    # ASSERT
    component_version_repo_mock.update_entity.assert_not_called()
    uow_mock.commit.assert_not_called()
