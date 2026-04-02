from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import ATTRIBUTE_NAME_ENTITY, DBPrefix, PagingParams
from app.packaging.domain.model.component import component, component_project_association
from app.packaging.domain.ports import component_query_service


class DynamoDBComponentQueryService(component_query_service.ComponentQueryService):
    """Component DynamoDB repository query service."""

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

    def get_components(self, project_id: str) -> list[component.Component]:
        """Returns the list of all components for the given project."""

        components: list[component.Component] = []
        components_ids: list[str] = []
        query_components_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key(ATTRIBUTE_NAME_ENTITY).eq(DBPrefix.Component),
            "IndexName": self._gsi_name_entities,
        }
        query_components_ids_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("SK").eq(f"{DBPrefix.Project}#{project_id}")
            & Key("PK").begins_with(f"{DBPrefix.Component}#"),
            "IndexName": self._gsi_inverted_primary_key,
        }

        if self._default_page_size:
            query_components_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size
            query_components_ids_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_components_kwargs)):
            query_components_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            components.extend(
                [component.Component.model_validate(component_obj) for component_obj in result.get("Items", [])]
            )

        components.extend(
            [component.Component.model_validate(component_obj) for component_obj in result.get("Items", [])]
        )

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_components_ids_kwargs)):
            query_components_ids_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            components_ids.extend(
                [attr_dict.get("PK").removeprefix(f"{DBPrefix.Component}#") for attr_dict in result.get("Items", [])]
            )

        components_ids.extend(
            [attr_dict.get("PK").removeprefix(f"{DBPrefix.Component}#") for attr_dict in result.get("Items", [])]
        )

        return [component_entity for component_entity in components if component_entity.componentId in components_ids]

    def get_component(self, component_id: str) -> component.Component | None:
        """Return component for given component id."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Component}#{component_id}",
                "SK": f"{DBPrefix.Component}#{component_id}",
            },
        )

        if "Item" in result:
            return component.Component.model_validate(result.get("Item"))
        else:
            return None

    def get_component_project_associations(
        self, component_id: str
    ) -> list[component_project_association.ComponentProjectAssociation]:
        """Return component for given component associations."""

        components: list[component_project_association.ComponentProjectAssociation] = []
        db_components: list[dict] = []
        query_key_cond = Key("PK").eq(f"{DBPrefix.Component}#{component_id}") & Key("SK").begins_with(
            f"{DBPrefix.Project}#"
        )
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": query_key_cond,
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            db_components.extend(result.get("Items", []))

        db_components.extend(result.get("Items", []))

        components = [
            component_project_association.ComponentProjectAssociation.model_validate(item) for item in db_components
        ]

        return components
