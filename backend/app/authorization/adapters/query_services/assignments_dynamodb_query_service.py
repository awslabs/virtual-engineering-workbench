from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.authorization.adapters.repository import dynamo_entity_config
from app.authorization.domain.ports import assignments_query_service
from app.authorization.domain.read_models import project_assignment


class AssignmentsDynamoDBQueryService(assignments_query_service.AssignmentsQueryService):

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_inverted_pk: str,
    ):
        super().__init__()
        self.__table_name = table_name
        self.__dynamodb_client = dynamodb_client
        self.__gsi_inverted_pk = gsi_inverted_pk

    def get_user_assignments(self, user_id: str) -> list[project_assignment.Assignment]:

        paginator = self.__dynamodb_client.get_paginator("query")
        ret_val: list[project_assignment.Assignment] = []

        pages = paginator.paginate(
            TableName=self.__table_name,
            KeyConditionExpression=Key("PK").eq(f"{dynamo_entity_config.DBPrefix.USER.value}#{user_id}")
            & Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#"),
        )
        for page in pages:
            ret_val.extend([project_assignment.Assignment.model_validate(item) for item in page["Items"]])

        return ret_val

    def get_project_assignments(self, project_id: str) -> list[project_assignment.Assignment]:
        paginator = self.__dynamodb_client.get_paginator("query")
        ret_val: list[project_assignment.Assignment] = []

        pages = paginator.paginate(
            TableName=self.__table_name,
            KeyConditionExpression=Key("SK").eq(f"{dynamo_entity_config.DBPrefix.PROJECT.value}#{project_id}")
            & Key("PK").begins_with(f"{dynamo_entity_config.DBPrefix.USER.value}#"),
            IndexName=self.__gsi_inverted_pk,
        )
        for page in pages:
            ret_val.extend([project_assignment.Assignment.model_validate(item) for item in page["Items"]])

        return ret_val
