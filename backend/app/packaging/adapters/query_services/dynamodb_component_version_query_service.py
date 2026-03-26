import natsort
from boto3.dynamodb.conditions import Attr, Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.packaging.domain.model.component import component, component_version, component_version_summary
from app.packaging.domain.ports import component_version_query_service


class DynamoDBComponentVersionQueryService(component_version_query_service.ComponentVersionQueryService):
    """Component version DynamoDB repository query service."""

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

    def get_latest_component_version_name(self, component_id: str) -> str | None:
        """Return latest version name for the given component."""

        sorted_component_version_names = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Component}#{component_id}")
            & Key("SK").begins_with(f"{DBPrefix.Version}#"),
            "ProjectionExpression": "componentVersionName",
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        component_version_names_paging: list[str] = []

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            component_version_names_paging.extend(
                [attr_dict.get("componentVersionName") for attr_dict in result.get("Items", [])]
            )

        component_version_names_paging.extend(
            [attr_dict.get("componentVersionName") for attr_dict in result.get("Items", [])]
        )
        sorted_component_version_names = natsort.natsorted(component_version_names_paging, reverse=True)

        return sorted_component_version_names[0] if sorted_component_version_names else None

    def get_component_versions(self, component_id: str) -> list[component_version.ComponentVersion]:
        """Returns the list of all versions for the given component."""

        component_versions: list[component_version.ComponentVersion] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Component}#{component_id}")
            & Key("SK").begins_with(f"{DBPrefix.Version}#"),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            component_versions.extend(result.get("Items", []))

        component_versions.extend(result.get("Items", []))

        return [component_version.ComponentVersion.parse_obj(obj) for obj in component_versions]

    def get_component_version(self, component_id: str, version_id: str) -> component_version.ComponentVersion | None:
        """Return a specific component version."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Component}#{component_id}",
                "SK": f"{DBPrefix.Version}#{version_id}",
            },
        )

        if "Item" in result:
            return component_version.ComponentVersion.parse_obj(result["Item"])
        else:
            return None

    def get_all_components_versions(
        self,
        status: component_version.ComponentVersionStatus,
        architecture: component.ComponentSupportedArchitectures,
        os: component.ComponentSupportedOsVersions,
        platform: component.ComponentPlatform,
    ) -> list[component_version_summary.ComponentVersionSummary]:
        """Returns a dictionary of all the component versions given a specific status, architecture, OS, and platform."""

        component_versions_summary: list[component_version_summary.ComponentVersionSummary] = []

        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_custom_query_by_status,
            "KeyConditionExpression": Key("GSI_PK").eq(f"{DBPrefix.Version}#{status}")
            & Key("GSI_SK").begins_with(f"{DBPrefix.Component}#"),
            "FilterExpression": Attr("componentSupportedArchitectures").contains(architecture)
            & Attr("componentSupportedOsVersions").contains(os)
            & Attr("componentPlatform").eq(platform),
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size
        dynamodb_result: list[component_version.ComponentVersion] = []
        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            dynamodb_result.extend(result.get("Items", []))
        dynamodb_result.extend(result.get("Items", []))
        for _component_version in dynamodb_result:
            parsed_component_version = component_version.ComponentVersion.parse_obj(_component_version)
            # Pydantic model can parse other objects and extracts only the attributes that it matches for the model.
            component_versions_summary.append(
                component_version_summary.ComponentVersionSummary.parse_obj(parsed_component_version)
            )
        return component_versions_summary
