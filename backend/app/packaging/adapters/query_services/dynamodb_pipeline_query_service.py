from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.ports import pipeline_query_service


class DynamoDBPipelineQueryService(pipeline_query_service.PipelineQueryService):
    """Pipeline DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_inverted_primary_key: str,
        gsi_name_entities: str,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_inverted_primary_key = gsi_inverted_primary_key
        self._gsi_name_entities = gsi_name_entities
        self._default_page_size = default_page_size

    def get_pipelines(self, project_id: str) -> list[pipeline.Pipeline]:
        """Returns the list of all pipelines for the given project."""

        pipelines: list[pipeline.Pipeline] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Project}#{project_id}")
            & Key("SK").begins_with(f"{DBPrefix.Pipeline}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            pipelines.extend(result.get("Items", []))

        pipelines.extend(result.get("Items", []))

        return [pipeline.Pipeline.parse_obj(obj) for obj in pipelines]

    def get_pipeline(self, project_id: str, pipeline_id: str) -> pipeline.Pipeline | None:
        """Return pipeline for given pipeline id."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Project}#{project_id}",
                "SK": f"{DBPrefix.Pipeline}#{pipeline_id}",
            },
        )

        if "Item" in result:
            return pipeline.Pipeline.parse_obj(result["Item"])
        else:
            return None

    def get_pipeline_by_pipeline_id(self, pipeline_id: str) -> pipeline.Pipeline | None:
        """Return pipeline for given pipeline id without filtering by project."""

        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("SK").eq(f"{DBPrefix.Pipeline}#{pipeline_id}")
            & Key("PK").begins_with(f"{DBPrefix.Project}#"),
            IndexName=self._gsi_inverted_primary_key,
        )

        # Only 1 result is returned at a time, hence we don't paginate
        if result.get("Items", []):
            project_id = result.get("Items", [])[0]["PK"].replace(f"{DBPrefix.Project}#", "")

            return self.get_pipeline(project_id=project_id, pipeline_id=pipeline_id)
        else:
            return None
