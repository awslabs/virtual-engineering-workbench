import typing

from boto3.dynamodb.conditions import Attr, Key
from mypy_boto3_dynamodb import client

from app.publishing.adapters.services.dynamo_db_repositories import DBPrefix
from app.publishing.domain.model import portfolio
from app.publishing.domain.ports import portfolios_query_service


class DynamoDBPortfoliosQueryService(portfolios_query_service.PortfoliosQueryService):
    """Portfolios DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_name_entities: str,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_name_entities = gsi_name_entities

    def get_portfolios_by_tech_and_stage(
        self, technology_id: str, portfolio_stage: str
    ) -> typing.List[portfolio.Portfolio]:
        portfolios = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.TECHNOLOGY.value}#{technology_id}")
            & Key("SK").begins_with(DBPrefix.AWS_ACCOUNT),
            "FilterExpression": Attr("stage").eq(portfolio_stage),
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
                portfolios.extend([portfolio.Portfolio.model_validate(item) for item in result["Items"]])

        return portfolios
