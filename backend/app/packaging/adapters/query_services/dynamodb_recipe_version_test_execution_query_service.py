from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.packaging.domain.model.recipe import recipe_version_test_execution
from app.packaging.domain.ports import recipe_version_test_execution_query_service


class DynamoDBRecipeVersionTestExecutionQueryService(
    recipe_version_test_execution_query_service.RecipeVersionTestExecutionQueryService
):
    """Recipe version test execution DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_name_entities: str,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_name_entities = gsi_name_entities
        self._default_page_size = default_page_size

    def get_recipe_version_test_executions(
        self, version_id: str
    ) -> list[recipe_version_test_execution.RecipeVersionTestExecution]:
        """Returns the list of all test executions for the given recipe version."""

        recipe_version_test_executions: list[recipe_version_test_execution.RecipeVersionTestExecution] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Version}#{version_id}")
            & Key("SK").begins_with(f"{DBPrefix.Execution}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            recipe_version_test_executions.extend(result.get("Items", []))

        recipe_version_test_executions.extend(result.get("Items", []))

        return [
            recipe_version_test_execution.RecipeVersionTestExecution.model_validate(obj)
            for obj in recipe_version_test_executions
        ]

    def get_recipe_version_test_execution(
        self, version_id: str, test_execution_id: str
    ) -> recipe_version_test_execution.RecipeVersionTestExecution | None:
        """Return a specific recipe version test execution."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Version}#{version_id}",
                "SK": f"{DBPrefix.Execution}#{test_execution_id}",
            },
        )

        if "Item" in result:
            return recipe_version_test_execution.RecipeVersionTestExecution.model_validate(result.get("Item"))
        else:
            return None
