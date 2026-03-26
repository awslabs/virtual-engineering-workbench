from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix
from app.packaging.domain.model.component import component, mandatory_components_list
from app.packaging.domain.ports import mandatory_components_list_query_service


class DynamoDBMandatoryComponentsListQueryService(
    mandatory_components_list_query_service.MandatoryComponentsListQueryService
):
    """Mandatory components list DynamoDB repository query service."""

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

    def get_mandatory_components_list(
        self, platform: str, os: str, architecture: str
    ) -> mandatory_components_list.MandatoryComponentsList | None:
        """Returns the mandatory components list for the given platform, OS, and architecture."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Platform}#{platform}",
                "SK": f"{DBPrefix.Os}#{os}#{DBPrefix.Arch}#{architecture}",
            },
        )

        if "Item" in result:
            return mandatory_components_list.MandatoryComponentsList.parse_obj(result["Item"])
        else:
            return None

    def get_mandatory_components_lists(self) -> list[mandatory_components_list.MandatoryComponentsList]:
        """Returns all the mandatory components lists."""

        mandatory_components_lists = list()
        for platform in component.ComponentPlatform.list():
            query_kwargs = {
                "TableName": self._table_name,
                "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Platform}#{platform}"),
            }
            query_result = self._dynamodb_client.query(**query_kwargs)
            mandatory_components_lists.extend(query_result.get("Items", []))

        return [mandatory_components_list.MandatoryComponentsList.parse_obj(obj) for obj in mandatory_components_lists]
