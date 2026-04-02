import assertpy

from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.recipe import recipe


def fill_db_with_recipes(backend_app_table, recipes: list[recipe.Recipe]):
    for reci in recipes:
        backend_app_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.Project}#{reci.projectId}",
                "SK": f"{dynamo_entity_config.DBPrefix.Recipe}#{reci.recipeId}",
                **reci.model_dump(),
            }
        )


def test_get_recipes(mock_dynamodb, get_mock_recipe, backend_app_table, get_recipe_query_service):
    # ARRANGE
    query_service = get_recipe_query_service
    fill_db_with_recipes(
        backend_app_table,
        [
            get_mock_recipe(project_id="proj-1", recipe_id="reci-1"),
            get_mock_recipe(project_id="proj-1", recipe_id="reci-2"),
            get_mock_recipe(project_id="proj-2", recipe_id="reci-3"),
            get_mock_recipe(project_id="proj-2", recipe_id="reci-4"),
        ],
    )

    # ACT
    recipes_proj_1 = query_service.get_recipes(project_id="proj-1")
    recipes_proj_2 = query_service.get_recipes(project_id="proj-2")
    recipes_proj_3 = query_service.get_recipes(project_id="proj-3")

    # ASSERT
    assertpy.assert_that(recipes_proj_1).is_not_none()
    assertpy.assert_that(recipes_proj_2).is_not_none()
    assertpy.assert_that(recipes_proj_3).is_not_none()
    assertpy.assert_that(len(recipes_proj_1)).is_equal_to(2)
    assertpy.assert_that(len(recipes_proj_2)).is_equal_to(2)
    assertpy.assert_that(len(recipes_proj_3)).is_equal_to(0)


def test_get_recipe(mock_dynamodb, get_mock_recipe, backend_app_table, get_recipe_query_service):
    # ARRANGE
    query_service = get_recipe_query_service
    fill_db_with_recipes(backend_app_table, [get_mock_recipe()])

    # ACT
    recipe_entity = query_service.get_recipe(
        project_id=GlobalVariables.TEST_PROJECT_ID.value, recipe_id=GlobalVariables.TEST_RECIPE_ID.value
    )

    # ASSERT
    assertpy.assert_that(recipe_entity).is_not_none()
    assertpy.assert_that(recipe_entity).is_equal_to(get_mock_recipe())


def test_get_recipe_returns_none_when_not_found(mock_dynamodb, backend_app_table, get_recipe_query_service):
    # ARRANGE
    query_service = get_recipe_query_service

    # ACT
    recipe_entity = query_service.get_recipe(
        project_id=GlobalVariables.TEST_PROJECT_ID.value, recipe_id=GlobalVariables.TEST_RECIPE_ID.value
    )

    # ASSERT
    assertpy.assert_that(recipe_entity).is_equal_to(None)
