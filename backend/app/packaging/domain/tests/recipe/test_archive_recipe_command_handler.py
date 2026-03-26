from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.packaging.domain.command_handlers.recipe import archive_recipe_command_handler
from app.packaging.domain.commands.recipe import archive_recipe_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.recipe import recipe, recipe_version
from app.packaging.domain.tests.conftest import TEST_PROJECT_ID, TEST_RECIPE_ID, TEST_USER_ID
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


@pytest.fixture()
def get_archive_recipe_command_mock():
    def _get_archive_recipe_command_mock():
        return archive_recipe_command.ArchiveRecipeCommand(
            projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
            recipeId=recipe_id_value_object.from_str(TEST_RECIPE_ID),
            lastUpdatedBy=user_id_value_object.from_str(TEST_USER_ID),
        )

    return _get_archive_recipe_command_mock


def test_handle_should_raise_an_exception_when_recipe_is_not_found(
    recipe_query_service_mock, recipe_version_query_service_mock, get_archive_recipe_command_mock, uow_mock
):
    # ARRANGE
    archive_recipe_command_mock = get_archive_recipe_command_mock()
    recipe_query_service_mock.get_recipe.return_value = None

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        archive_recipe_command_handler.handle(
            command=archive_recipe_command_mock,
            recipe_qry_srv=recipe_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe {archive_recipe_command_mock.recipeId.value} can not be found."
    )


@pytest.mark.parametrize(
    "recipes_versions_statuses",
    (
        [
            recipe_version.RecipeVersionStatus.Created,
        ],
        [
            recipe_version.RecipeVersionStatus.Created,
            recipe_version.RecipeVersionStatus.Retired,
        ],
        [
            recipe_version.RecipeVersionStatus.Creating,
        ],
        [
            recipe_version.RecipeVersionStatus.Failed,
        ],
        [
            recipe_version.RecipeVersionStatus.Released,
        ],
        [
            recipe_version.RecipeVersionStatus.Retired,
            recipe_version.RecipeVersionStatus.Created,
        ],
        [
            recipe_version.RecipeVersionStatus.Testing,
        ],
        [
            recipe_version.RecipeVersionStatus.Updating,
        ],
        [
            recipe_version.RecipeVersionStatus.Validated,
        ],
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_raise_an_exception_when_a_recipe_version_status_is_invalid(
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    recipes_versions_statuses,
    get_archive_recipe_command_mock,
    mock_recipe_object,
    get_test_recipe_version_with_specific_status,
    uow_mock,
):
    # ARRANGE
    archive_recipe_command_mock = get_archive_recipe_command_mock()
    recipe_query_service_mock.get_recipe.return_value = mock_recipe_object
    recipe_versions_entities = [
        get_test_recipe_version_with_specific_status(status=status) for status in recipes_versions_statuses
    ]
    recipe_version_query_service_mock.get_recipe_versions.return_value = recipe_versions_entities
    recipe_version_invalid_status_entity = [
        recipe_version_entity
        for recipe_version_entity in recipe_versions_entities
        if recipe_version_entity.status is not recipe_version.RecipeVersionStatus.Retired
    ][0]

    # ACT
    with pytest.raises(domain_exception.DomainException) as e:
        archive_recipe_command_handler.handle(
            command=archive_recipe_command_mock,
            recipe_qry_srv=recipe_query_service_mock,
            recipe_version_qry_srv=recipe_version_query_service_mock,
            uow=uow_mock,
        )

    # ASSERT
    assertpy.assert_that(str(e.value)).is_equal_to(
        f"Recipe {archive_recipe_command_mock.recipeId.value} cannot be retired because recipe version "
        f"{recipe_version_invalid_status_entity.recipeVersionId} is in {recipe_version_invalid_status_entity.status} status."
    )


@pytest.mark.parametrize(
    "recipes_versions_statuses",
    (
        [],
        [
            recipe_version.RecipeVersionStatus.Retired,
        ],
        [
            recipe_version.RecipeVersionStatus.Retired,
            recipe_version.RecipeVersionStatus.Retired,
        ],
    ),
)
@freeze_time("2023-10-12")
def test_handle_should_archive_component(
    recipe_query_service_mock,
    recipe_version_query_service_mock,
    recipes_versions_statuses,
    get_archive_recipe_command_mock,
    mock_recipe_object,
    get_test_recipe_version_with_specific_status,
):
    # ARRANGE
    archive_recipe_command_mock = get_archive_recipe_command_mock()
    recipe_repository_mock = mock.create_autospec(spec=unit_of_work.GenericRepository)
    recipe_version_query_service_mock.get_recipe_versions.return_value = [
        get_test_recipe_version_with_specific_status(status=status) for status in recipes_versions_statuses
    ]
    repositories_dictionary = {recipe.Recipe: recipe_repository_mock}
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)

    uow_mock.get_repository.side_effect = lambda pk, x: repositories_dictionary.get(x)

    # ACT
    archive_recipe_command_handler.handle(
        command=archive_recipe_command_mock,
        recipe_qry_srv=recipe_query_service_mock,
        recipe_version_qry_srv=recipe_version_query_service_mock,
        uow=uow_mock,
    )

    # ASSERT
    recipe_repository_mock.update_attributes.assert_called_once_with(
        recipe.RecipePrimaryKey(
            projectId=archive_recipe_command_mock.projectId.value, recipeId=archive_recipe_command_mock.recipeId.value
        ),
        lastUpdateBy=archive_recipe_command_mock.lastUpdatedBy.value,
        lastUpdateDate="2023-10-12T00:00:00+00:00",
        status=recipe.RecipeStatus.Archived,
    )
    uow_mock.commit.assert_called()
