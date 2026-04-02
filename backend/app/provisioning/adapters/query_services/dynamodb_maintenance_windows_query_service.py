from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.provisioning.domain.model import maintenance_window
from app.provisioning.domain.ports import maintenance_windows_query_service


class DynamoDBMaintenanceWindowsQueryService(maintenance_windows_query_service.MaintenanceWindowsQueryService):
    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_inverted_primary_key: str,
        default_page_size: int | None = None,
    ) -> None:
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_inverted_primary_key = gsi_inverted_primary_key
        self._default_page_size = default_page_size
        self._entity_config = dynamo_entity_config.EntityConfigurator(table_name=table_name)

    def get_maintenance_windows_by_user_id(self, user_id: str) -> list[maintenance_window.MaintenanceWindow]:
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("SK").eq(f"{DBPrefix.USER.value}#{user_id}"),
            "IndexName": self._gsi_inverted_primary_key,
        }

        raw_items = []

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            raw_items.extend(result.get("Items", []))

        raw_items.extend(result.get("Items", []))

        maintenance_windows = [maintenance_window.MaintenanceWindow.model_validate(item) for item in raw_items]

        return maintenance_windows

    def get_maintenance_windows_by_time(
        self, day: maintenance_window.WeekDay, start_hour: int
    ) -> list[maintenance_window.MaintenanceWindow]:
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.MAINTENANCE_WINDOW.value}#{day.value}#{start_hour}")
            & Key("SK").begins_with(f"{DBPrefix.USER.value}#"),
        }

        raw_items = []

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            raw_items.extend(result.get("Items", []))

        raw_items.extend(result.get("Items", []))

        maintenance_windows = [maintenance_window.MaintenanceWindow.model_validate(item) for item in raw_items]

        return maintenance_windows
