import natsort
from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.packaging.domain.model.recipe import recipe_version, recipe_version_summary
from app.packaging.domain.ports import recipe_version_query_service


class DynamoDBRecipeVersionQueryService(recipe_version_query_service.RecipeVersionQueryService):
    """Recipe version DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_custom_query_by_status: str,
        gsi_name_entities: str,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_custom_query_by_status = gsi_custom_query_by_status
        self._gsi_name_entities = gsi_name_entities
        self._default_page_size = default_page_size

    def get_latest_recipe_version_name(self, recipe_id: str) -> str | None:
        """Return latest version name for the given recipe."""

        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Recipe}#{recipe_id}")
            & Key("SK").begins_with(f"{DBPrefix.Version}#"),
            "ProjectionExpression": "recipeVersionName",
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        recipe_version_names_paging: list[str] = []
        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            recipe_version_names_paging.extend(
                [attr_dict.get("recipeVersionName") for attr_dict in result.get("Items", [])]
            )

        recipe_version_names_paging.extend(
            [attr_dict.get("recipeVersionName") for attr_dict in result.get("Items", [])]
        )
        sorted_recipe_version_names = natsort.natsorted(recipe_version_names_paging, reverse=True)

        return sorted_recipe_version_names[0] if sorted_recipe_version_names else None

    def get_recipe_versions(self, recipe_id: str) -> list[recipe_version.RecipeVersion]:
        """Returns the list of all versions for the given recipe."""

        recipe_versions: list[recipe_version.RecipeVersion] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Recipe}#{recipe_id}")
            & Key("SK").begins_with(f"{DBPrefix.Version}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            recipe_versions.extend(result.get("Items", []))

        recipe_versions.extend(result.get("Items", []))

        return [recipe_version.RecipeVersion.parse_obj(obj) for obj in recipe_versions]

    def get_recipe_version(self, recipe_id: str, version_id: str) -> recipe_version.RecipeVersion | None:
        """Return a specific recipe version."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Recipe}#{recipe_id}",
                "SK": f"{DBPrefix.Version}#{version_id}",
            },
        )

        if "Item" in result:
            return recipe_version.RecipeVersion.parse_obj(result.get("Item"))
        else:
            return None

    def get_all_recipe_versions(
        self,
        status: recipe_version.RecipeVersionStatus,
    ) -> list[recipe_version_summary.RecipeVersionSummary]:
        """Returns a dictionary of all the recipe versions given a specific status"""

        recipe_versions_summary: list[recipe_version_summary.RecipeVersionSummary] = []

        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_custom_query_by_status,
            "KeyConditionExpression": Key("GSI_PK").eq(f"{DBPrefix.Version}#{status}")
            & Key("GSI_SK").begins_with(f"{DBPrefix.Recipe}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size
        dynamodb_result: list[recipe_version.RecipeVersion] = []
        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            dynamodb_result.extend(result.get("Items", []))
        dynamodb_result.extend(result.get("Items", []))
        for _recipe_version in dynamodb_result:
            parsed_component_version = recipe_version.RecipeVersion.parse_obj(_recipe_version)
            # Pydantic model can parse other objects and extracts only the attributes that it matches for the model.
            recipe_versions_summary.append(
                recipe_version_summary.RecipeVersionSummary.parse_obj(parsed_component_version)
            )
        return recipe_versions_summary
