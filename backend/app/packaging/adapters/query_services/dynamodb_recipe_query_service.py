from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.packaging.domain.model.recipe import recipe
from app.packaging.domain.ports import recipe_query_service


class DynamoDBRecipeQueryService(recipe_query_service.RecipeQueryService):
    """Recipe DynamoDB repository query service."""

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

    def get_recipes(self, project_id: str) -> list[recipe.Recipe]:
        """Returns the list of all recipes for the given project."""

        recipes: list[recipe.Recipe] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Project}#{project_id}")
            & Key("SK").begins_with(f"{DBPrefix.Recipe}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            recipes.extend(result.get("Items", []))

        recipes.extend(result.get("Items", []))

        return [recipe.Recipe.model_validate(obj) for obj in recipes]

    def get_recipe(self, project_id: str, recipe_id: str) -> recipe.Recipe | None:
        """Return recipe for given recipe id."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Project}#{project_id}",
                "SK": f"{DBPrefix.Recipe}#{recipe_id}",
            },
        )

        if "Item" in result:
            return recipe.Recipe.model_validate(result["Item"])
        else:
            return None
