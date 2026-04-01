from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.publishing.adapters.services.dynamo_db_repositories import ATTRIBUTE_NAME_ENTITY, DBPrefix
from app.publishing.domain.ports import amis_query_service
from app.publishing.domain.read_models import ami


class DynamoDBAMIsQueryService(amis_query_service.AMIsQueryService):
    """AMI DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_name_entities: str,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_name_entities = gsi_name_entities

    def get_amis(self, project_id: str) -> list[ami.Ami]:
        """Return list of available AMIs for a project"""

        amis = []
        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_name_entities,
            "KeyConditionExpression": Key(ATTRIBUTE_NAME_ENTITY).eq(DBPrefix.AMI.value),
            "FilterExpression": Key("projectId").eq(project_id),
        }

        done = False
        start_key = None

        while not done:
            if start_key:
                query_kwargs["ExclusiveStartKey"] = start_key
            result = self._dynamodb_client.query(**query_kwargs)

            start_key = result.get("LastEvaluatedKey", None)
            done = start_key is None
            if result.get("Items"):
                amis.extend([ami.Ami.model_validate(item) for item in result["Items"]])

        return amis

    def get_ami(self, ami_id: str) -> ami.Ami:
        """Return AMI with given id"""

        response = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.AMI.value}#{ami_id}",
                "SK": f"{DBPrefix.AMI.value}#{ami_id}",
            },
        )

        if item := response.get("Item"):
            return ami.Ami.model_validate(item)
        return None
