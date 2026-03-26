from unittest import mock

import assertpy

from app.packaging.domain.command_handlers.recipe import check_recipe_version_release_status_command_handler
from app.packaging.domain.commands.recipe import check_recipe_version_release_status_command
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object


def test_handle_should_return_released_when_recipe_version_is_released():
    # ARRANGE
    # Mock dependencies
    recipe_version_query_service_mock = mock.Mock()

    # Create command
    command = check_recipe_version_release_status_command.CheckRecipeVersionReleaseStatusCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        recipeVersionId=recipe_version_id_value_object.from_str("version-12345"),
    )

    # Mock recipe version
    recipe_version_mock = mock.Mock()
    recipe_version_mock.status = recipe_version.RecipeVersionStatus.Released
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_mock

    # ACT
    result = check_recipe_version_release_status_command_handler.handle(
        command=command,
        recipe_version_query_service=recipe_version_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["recipeVersionStatus"]).is_equal_to(recipe_version.RecipeVersionStatus.Released.value)
    recipe_version_query_service_mock.get_recipe_version.assert_called_once_with(
        recipe_id=command.recipeId.value,
        version_id=command.recipeVersionId.value,
    )


def test_handle_should_return_failed_when_recipe_version_is_failed():
    # ARRANGE
    # Mock dependencies
    recipe_version_query_service_mock = mock.Mock()

    # Create command
    command = check_recipe_version_release_status_command.CheckRecipeVersionReleaseStatusCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        recipeVersionId=recipe_version_id_value_object.from_str("version-12345"),
    )

    # Mock recipe version
    recipe_version_mock = mock.Mock()
    recipe_version_mock.status = recipe_version.RecipeVersionStatus.Failed
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_mock

    # ACT
    result = check_recipe_version_release_status_command_handler.handle(
        command=command,
        recipe_version_query_service=recipe_version_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["recipeVersionStatus"]).is_equal_to(recipe_version.RecipeVersionStatus.Failed.value)


def test_handle_should_return_in_progress_when_recipe_version_is_validated():
    # ARRANGE
    # Mock dependencies
    recipe_version_query_service_mock = mock.Mock()

    # Create command
    command = check_recipe_version_release_status_command.CheckRecipeVersionReleaseStatusCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        recipeVersionId=recipe_version_id_value_object.from_str("version-12345"),
    )

    # Mock recipe version
    recipe_version_mock = mock.Mock()
    recipe_version_mock.status = recipe_version.RecipeVersionStatus.Validated
    recipe_version_query_service_mock.get_recipe_version.return_value = recipe_version_mock

    # ACT
    result = check_recipe_version_release_status_command_handler.handle(
        command=command,
        recipe_version_query_service=recipe_version_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["recipeVersionStatus"]).is_equal_to(recipe_version.RecipeVersionStatus.Updating.value)


def test_handle_should_return_failed_when_recipe_version_not_found():
    # ARRANGE
    # Mock dependencies
    recipe_version_query_service_mock = mock.Mock()

    # Create command
    command = check_recipe_version_release_status_command.CheckRecipeVersionReleaseStatusCommand(
        recipeId=recipe_id_value_object.from_str("recipe-12345"),
        recipeVersionId=recipe_version_id_value_object.from_str("version-12345"),
    )

    # Mock recipe version not found
    recipe_version_query_service_mock.get_recipe_version.return_value = None

    # ACT
    result = check_recipe_version_release_status_command_handler.handle(
        command=command,
        recipe_version_query_service=recipe_version_query_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result["recipeVersionStatus"]).is_equal_to(recipe_version.RecipeVersionStatus.Failed.value)
