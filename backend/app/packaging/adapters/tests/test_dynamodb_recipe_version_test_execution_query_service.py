import assertpy

from app.packaging.adapters.query_services import dynamodb_recipe_version_test_execution_query_service
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.tests.conftest import GlobalVariables
from app.packaging.domain.model.recipe import recipe_version_test_execution


def fill_db_with_test_executions(
    backend_app_table,
    recipe_version_test_executions: list[recipe_version_test_execution.RecipeVersionTestExecution],
):
    for test_execution in recipe_version_test_executions:
        backend_app_table.put_item(
            Item={
                "PK": f"{dynamo_entity_config.DBPrefix.Version}#{test_execution.recipeVersionId}",
                "SK": "#".join([dynamo_entity_config.DBPrefix.Execution, test_execution.testExecutionId]),
                **test_execution.model_dump(),
            }
        )


def test_get_recipe_version_test_executions(
    mock_dynamodb,
    get_mock_recipe_version_test_execution,
    backend_app_table,
    get_mock_recipe_version,
    get_mock_recipe,
    get_recipe_version_test_execution_query_service,
):
    # ARRANGE
    query_service = get_recipe_version_test_execution_query_service
    fill_db_with_test_executions(
        backend_app_table,
        [
            get_mock_recipe_version_test_execution(),
            get_mock_recipe_version_test_execution(
                recipe_version_id="version-2",
            ),
            get_mock_recipe_version_test_execution(
                recipe_version_id="version-2",
                test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044",
            ),
        ],
    )

    # ACT
    recipe_version_test_executions_1 = query_service.get_recipe_version_test_executions(
        version_id=get_mock_recipe_version().recipeVersionId
    )
    recipe_version_test_executions_2 = query_service.get_recipe_version_test_executions(version_id="version-2")
    recipe_version_test_executions_3 = query_service.get_recipe_version_test_executions(version_id="version-3")

    # ASSERT
    assertpy.assert_that(recipe_version_test_executions_1).is_not_none()
    assertpy.assert_that(recipe_version_test_executions_2).is_not_none()
    assertpy.assert_that(recipe_version_test_executions_3).is_not_none()
    assertpy.assert_that(len(recipe_version_test_executions_1)).is_equal_to(1)
    assertpy.assert_that(len(recipe_version_test_executions_2)).is_equal_to(2)
    assertpy.assert_that(len(recipe_version_test_executions_3)).is_equal_to(0)


def test_get_recipe_version_test_execution(
    mock_dynamodb,
    get_mock_recipe_version_test_execution,
    backend_app_table,
    get_mock_recipe_version,
    get_mock_recipe,
    get_recipe_version_test_execution_query_service,
):
    # ARRANGE
    query_service = dynamodb_recipe_version_test_execution_query_service.DynamoDBRecipeVersionTestExecutionQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=get_recipe_version_test_execution_query_service,
    )
    fill_db_with_test_executions(
        backend_app_table,
        [get_mock_recipe_version_test_execution()],
    )

    # ACT
    recipe_version = query_service.get_recipe_version_test_execution(
        version_id=get_mock_recipe_version().recipeVersionId,
        test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(recipe_version).is_not_none()
    assertpy.assert_that(recipe_version).is_equal_to(get_mock_recipe_version_test_execution())


def test_get_recipe_version_test_execution_by_test_execution_id(
    mock_dynamodb,
    get_mock_recipe_version_test_execution,
    backend_app_table,
    get_mock_recipe_version,
    get_mock_recipe,
    get_recipe_version_test_execution_query_service,
):
    # ARRANGE
    query_service = get_recipe_version_test_execution_query_service
    fill_db_with_test_executions(
        backend_app_table,
        [
            get_mock_recipe_version_test_execution(),
            get_mock_recipe_version_test_execution(
                recipe_version_id="version-2",
            ),
            get_mock_recipe_version_test_execution(
                recipe_version_id="version-2",
                test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044",
            ),
        ],
    )

    # ACT
    recipe_version_test_executions_1 = query_service.get_recipe_version_test_execution(
        version_id=get_mock_recipe_version().recipeVersionId,
        test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
    )
    recipe_version_test_executions_2 = query_service.get_recipe_version_test_execution(
        version_id="version-2",
        test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
    )
    recipe_version_test_executions_3 = query_service.get_recipe_version_test_execution(
        version_id="version-2", test_execution_id="09776d9f-349f-4f50-8ba4-b862d8eaa044"
    )

    # ASSERT
    assertpy.assert_that(recipe_version_test_executions_1).is_not_none()
    assertpy.assert_that(recipe_version_test_executions_2).is_not_none()
    assertpy.assert_that(recipe_version_test_executions_3).is_not_none()
    assertpy.assert_that(recipe_version_test_executions_1.recipeVersionId).is_equal_to(
        get_mock_recipe_version().recipeVersionId
    )
    assertpy.assert_that(recipe_version_test_executions_2.recipeVersionId).is_equal_to("version-2")
    assertpy.assert_that(recipe_version_test_executions_2.testExecutionId).is_equal_to(
        GlobalVariables.TEST_TEST_EXECUTION_ID.value,
    )
    assertpy.assert_that(recipe_version_test_executions_3.recipeVersionId).is_equal_to("version-2")
    assertpy.assert_that(recipe_version_test_executions_3.testExecutionId).is_equal_to(
        "09776d9f-349f-4f50-8ba4-b862d8eaa044"
    )


def test_get_recipe_version_test_execution_returns_none_when_not_found(
    mock_dynamodb,
    get_mock_recipe_version,
    get_mock_recipe,
    backend_app_table,
    get_recipe_version_test_execution_query_service,
):
    # ARRANGE
    query_service = get_recipe_version_test_execution_query_service

    # ACT
    recipe_version_test_execution_entity = query_service.get_recipe_version_test_execution(
        version_id=get_mock_recipe_version().recipeVersionId,
        test_execution_id=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
    )

    # ASSERT
    assertpy.assert_that(recipe_version_test_execution_entity).is_equal_to(None)
