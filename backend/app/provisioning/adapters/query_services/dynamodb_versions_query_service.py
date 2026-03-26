from boto3.dynamodb.conditions import Attr, AttributeBase, ConditionBase, Key
from mypy_boto3_dynamodb import client

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_config import DBPrefix
from app.provisioning.domain.ports import versions_query_service
from app.provisioning.domain.read_models import version

DDB_RESPONSE_PAGING_PARAM = "LastEvaluatedKey"
DDB_REQUEST_PAGING_PARAM = "ExclusiveStartKey"
DDB_PAGE_SIZE_PARAM = "Limit"


class DynamoDBVersionsQueryService(versions_query_service.VersionsQueryService):
    """Versions DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_name_query_by_sc_pa_id: str,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._default_page_size = default_page_size
        self._gsi_name_query_by_sc_pa_id = gsi_name_query_by_sc_pa_id

    def get_product_version_distributions(
        self,
        product_id: str,
        version_id: str | None = None,
        aws_account_ids: list[str] | None = None,
        is_recommended: bool | None = None,
        region: str | None = None,
        stage: version.VersionStage | None = None,
    ) -> list[version.Version]:
        """Return version distribution"""

        key_condition_expression: ConditionBase = Key("PK").eq(
            f"{dynamo_entity_config.DBPrefix.PRODUCT}#{product_id}"
        ) & self._get_version_id_criteria(version_id=version_id)

        query_params = {
            "TableName": self._table_name,
            "KeyConditionExpression": key_condition_expression,
            "ConsistentRead": True,
        }

        filter_expression = self._get_filter_expression(
            aws_account_ids=aws_account_ids,
            is_recommended=is_recommended,
            region=region,
            stage=stage,
        )

        if filter_expression:
            query_params["FilterExpression"] = filter_expression

        if self._default_page_size:
            query_params[DDB_PAGE_SIZE_PARAM] = self._default_page_size

        versions: list[version.Version] = []
        while DDB_RESPONSE_PAGING_PARAM in (result := self._dynamodb_client.query(**query_params)):
            query_params[DDB_REQUEST_PAGING_PARAM] = result.get(DDB_RESPONSE_PAGING_PARAM)
            versions.extend([version.Version.parse_obj(item) for item in result["Items"]])

        versions.extend([version.Version.parse_obj(item) for item in result["Items"]])

        return versions

    def get_product_version_distribution(
        self,
        product_id: str,
        version_id: str,
        aws_account_id: str,
    ) -> version.Version | None:
        """Return version distribution"""
        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{dynamo_entity_config.DBPrefix.PRODUCT}#{product_id}",
                "SK": f"{dynamo_entity_config.DBPrefix.VERSION}#{version_id}#{dynamo_entity_config.DBPrefix.AWS_ACCOUNT}#{aws_account_id}",
            },
        )

        if "Item" in result:
            return version.Version.parse_obj(result["Item"])
        else:
            return None

    def get_by_provisioning_artifact_id(self, sc_provisioning_artifact_id: str) -> version.Version | None:

        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("QPK_1").eq(f"{DBPrefix.SC_PROVISIONING_ARTIFACT}#{sc_provisioning_artifact_id}")
            & Key("SK").begins_with(f"{DBPrefix.VERSION}#"),
            Limit=1,
            IndexName=self._gsi_name_query_by_sc_pa_id,
        )

        if len(result.get("Items")) > 1:
            raise adapter_exception.AdapterException(f"More than 1 versions found for {sc_provisioning_artifact_id}")

        if result.get("Items"):
            return version.Version.parse_obj(result["Items"][0])

        return None

    def _get_filter_expression(
        self,
        aws_account_ids: list[str] | None = None,
        is_recommended: bool | None = None,
        region: str | None = None,
        stage: str | None = None,
        version_name: str | None = None,
    ) -> AttributeBase | None:
        filter_expression: AttributeBase | None = None
        account_id_condition = self._get_account_id_criteria(aws_account_ids)
        recommended_condition = self._get_is_recommended_criteria(is_recommended)
        region_condition = self._get_region_criteria(region)
        stage_condition = self._get_stage_criteria(stage)
        version_name_contains_condition = self._get_version_name_contains_criteria(version_name)

        conditions = [
            account_id_condition,
            recommended_condition,
            region_condition,
            stage_condition,
            version_name_contains_condition,
        ]
        existing_conditions = filter(None, conditions)

        for condition in existing_conditions:
            filter_expression = filter_expression & condition if filter_expression else condition
        return filter_expression

    def _get_account_id_criteria(self, aws_account_ids: list[str] | None = None) -> AttributeBase | None:
        return Attr("awsAccountId").is_in(aws_account_ids) if aws_account_ids else None

    def _get_is_recommended_criteria(self, is_recommended: bool | None = None) -> AttributeBase | None:
        return Attr("isRecommendedVersion").eq(is_recommended) if is_recommended is not None else None

    def _get_region_criteria(
        self,
        region: str | None = None,
    ) -> AttributeBase | None:
        return Attr("region").eq(region) if region is not None else None

    def _get_stage_criteria(
        self,
        stage: str | None = None,
    ) -> AttributeBase | None:
        return Attr("stage").eq(stage) if stage is not None else None

    def _get_version_id_criteria(self, version_id: str | None = None) -> ConditionBase:
        if version_id:
            return Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.VERSION}#{version_id}#")
        else:
            return Key("SK").begins_with(f"{dynamo_entity_config.DBPrefix.VERSION}#")

    def _get_version_name_begins_with_criteria(self, version_name_begins_with: str) -> AttributeBase | None:
        return Attr("versionName").begins_with(version_name_begins_with) if version_name_begins_with else None

    def _get_version_name_contains_criteria(self, version_name: str | None = None) -> AttributeBase | None:
        return Attr("versionName").contains(version_name) if version_name else None
