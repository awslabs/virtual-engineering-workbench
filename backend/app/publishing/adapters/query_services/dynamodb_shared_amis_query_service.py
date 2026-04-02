from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.publishing.adapters.services.dynamo_db_repositories import DBPrefix
from app.publishing.domain.model import shared_ami
from app.publishing.domain.ports import shared_amis_query_service


class DynamoDBSharedAMIsQueryService(shared_amis_query_service.SharedAMIsQueryService):
    """Shared AMIs DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_name_entities: str,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_name_entities = gsi_name_entities

    def get_shared_amis(self, original_ami_id: str) -> list[shared_ami.SharedAmi]:
        """Returns a list of shared ami entities for the given original ami id"""

        shared_amis = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.AMI.value}#{original_ami_id}")
            & Key("SK").begins_with(f"{DBPrefix.AWS_ACCOUNT}#"),
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
                shared_amis.extend([shared_ami.SharedAmi.model_validate(item) for item in result["Items"]])

        return shared_amis
