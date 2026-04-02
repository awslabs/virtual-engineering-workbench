from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.packaging.domain.model.component import component_version_test_execution
from app.packaging.domain.ports import component_version_test_execution_query_service


class DynamoDBComponentVersionTestExecutionQueryService(
    component_version_test_execution_query_service.ComponentVersionTestExecutionQueryService
):
    """Component version test execution DynamoDB repository query service."""

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

    def get_component_version_test_executions(
        self, version_id: str
    ) -> list[component_version_test_execution.ComponentVersionTestExecution]:
        """Returns the list of all test executions for the given component version."""

        component_version_test_executions: list[component_version_test_execution.ComponentVersionTestExecution] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Version}#{version_id}")
            & Key("SK").begins_with(f"{DBPrefix.Execution}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            component_version_test_executions.extend(result.get("Items", []))

        component_version_test_executions.extend(result.get("Items", []))

        return [
            component_version_test_execution.ComponentVersionTestExecution.model_validate(obj)
            for obj in component_version_test_executions
        ]

    def get_component_version_test_execution(
        self, version_id: str, test_execution_id: str, instance_id: str
    ) -> component_version_test_execution.ComponentVersionTestExecution | None:
        """Return a specific component version test execution."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Version}#{version_id}",
                "SK": f"{DBPrefix.Execution}#{test_execution_id}#{DBPrefix.Instance}#{instance_id}",
            },
        )

        if "Item" in result:
            return component_version_test_execution.ComponentVersionTestExecution.model_validate(result["Item"])
        else:
            return None

    def get_component_version_test_executions_by_test_execution_id(
        self, version_id: str, test_execution_id: str
    ) -> list[component_version_test_execution.ComponentVersionTestExecution]:
        """Returns the list of all test executions for the given component version and test execution ID."""

        component_version_test_executions: list[component_version_test_execution.ComponentVersionTestExecution] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Version}#{version_id}")
            & Key("SK").begins_with(f"{DBPrefix.Execution}#{test_execution_id}#{DBPrefix.Instance}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            component_version_test_executions.extend(result.get("Items", []))

        component_version_test_executions.extend(result.get("Items", []))

        return [
            component_version_test_execution.ComponentVersionTestExecution.model_validate(obj)
            for obj in component_version_test_executions
        ]
