import typing

import natsort
from boto3.dynamodb.conditions import Attr, AttributeBase, ConditionBase, Key
from mypy_boto3_dynamodb import client

from app.publishing.adapters.services import dynamo_db_repositories
from app.publishing.domain.model import version
from app.publishing.domain.ports import versions_query_service

DDB_RESPONSE_PAGING_PARAM = "LastEvaluatedKey"
DDB_REQUEST_PAGING_PARAM = "ExclusiveStartKey"
DDB_PAGE_SIZE_PARAM = "Limit"


class DynamoDBVersionsQueryService(versions_query_service.VersionsQueryService):
    """Versions DynamoDB repository query service."""

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

    def get_latest_version_name_and_id(
        self, product_id: str, version_name_begins_with: str = None
    ) -> typing.Tuple[str | None, str | None]:
        """Return latest version name and version id for the given product"""

        sorted_version_names = []
        latest_version_name = None
        latest_version_id = None
        done = False
        start_key = None
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{dynamo_db_repositories.DBPrefix.PRODUCT.value}#{product_id}")
            & Key("SK").begins_with(f"{dynamo_db_repositories.DBPrefix.VERSION}#"),
            "ProjectionExpression": "versionName,versionId",
        }

        if version_name_begins_with:
            query_kwargs["FilterExpression"] = self._get_version_name_begins_with_criteria(version_name_begins_with)

        if self._default_page_size:
            query_kwargs[DDB_PAGE_SIZE_PARAM] = self._default_page_size

        versions_names: list[str] = []
        version_name_id_dict: dict[str, str] = {}

        while not done:
            if start_key:
                query_kwargs[DDB_REQUEST_PAGING_PARAM] = start_key
            result = self._dynamodb_client.query(**query_kwargs)
            start_key = result.get(DDB_RESPONSE_PAGING_PARAM, None)
            done = start_key is None
            for attr_dict in result.get("Items", []):
                versions_names.append(attr_dict.get("versionName"))
                version_name_id_dict[attr_dict.get("versionName")] = attr_dict.get("versionId")

        sorted_version_names = natsort.natsorted(versions_names, reverse=True)
        if sorted_version_names:
            latest_version_name = sorted_version_names[0]
            latest_version_id = version_name_id_dict[latest_version_name]

        return latest_version_name, latest_version_id

    def get_product_version_distributions(
        self,
        product_id: str,
        version_id: str | None = None,
        aws_account_ids: list[str] | None = None,
        is_recommended: bool | None = None,
        region: str | None = None,
        stage: version.VersionStage | None = None,
        statuses: list[version.VersionStatus] | None = None,
    ) -> list[version.Version]:
        """Return version distribution"""

        key_condition_expression: ConditionBase = Key("PK").eq(
            f"{dynamo_db_repositories.DBPrefix.PRODUCT}#{product_id}"
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
            statuses=statuses,
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
                "PK": f"{dynamo_db_repositories.DBPrefix.PRODUCT}#{product_id}",
                "SK": f"{dynamo_db_repositories.DBPrefix.VERSION}#{version_id}#{dynamo_db_repositories.DBPrefix.AWS_ACCOUNT}#{aws_account_id}",
            },
        )

        if "Item" in result:
            return version.Version.parse_obj(result["Item"])
        else:
            return None

    def get_distinct_number_of_versions(
        self, product_id: str, status: version.VersionStatus = None, version_name_filter: str = None
    ) -> int:
        key_condition_expression: ConditionBase = (
            Key("PK").eq(f"{dynamo_db_repositories.DBPrefix.PRODUCT}#{product_id}") & self._get_version_id_criteria()
        )

        query_params = {
            "TableName": self._table_name,
            "KeyConditionExpression": key_condition_expression,
            "ProjectionExpression": "versionId",
        }

        filter_expression = self._get_filter_expression(status=status, version_name=version_name_filter)

        if filter_expression:
            query_params["FilterExpression"] = filter_expression

        if self._default_page_size:
            query_params[DDB_PAGE_SIZE_PARAM] = self._default_page_size

        distinct_version_ids: typing.Set[str] = set()
        while DDB_RESPONSE_PAGING_PARAM in (result := self._dynamodb_client.query(**query_params)):
            query_params[DDB_REQUEST_PAGING_PARAM] = result.get(DDB_RESPONSE_PAGING_PARAM)
            distinct_version_ids.update({attr_dict.get("versionId") for attr_dict in result.get("Items", [])})

        distinct_version_ids.update({attr_dict.get("versionId") for attr_dict in result.get("Items", [])})

        return len(distinct_version_ids)

    def get_all_versions(self, region: str | None = None) -> list[version.Version]:
        """Returns all versions across all products"""

        query_params = {
            "TableName": self._table_name,
            "IndexName": self._gsi_name_entities,
            "KeyConditionExpression": Key("entity").eq(dynamo_db_repositories.DBPrefix.VERSION),
        }

        filter_expression = self._get_filter_expression(region=region)
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

    def get_used_ami_ids_in_all_versions(self, region: str | None = None) -> set[str]:
        """Returns all used ami ids in all versions in a given region"""

        query_params = {
            "TableName": self._table_name,
            "IndexName": self._gsi_name_entities,
            "KeyConditionExpression": Key("entity").eq(dynamo_db_repositories.DBPrefix.VERSION),
            "ProjectionExpression": "originalAmiId",
        }

        filter_expression = self._get_filter_expression(region=region, original_ami_id_exists=True)
        if filter_expression:
            query_params["FilterExpression"] = filter_expression

        used_ami_ids = set()
        while DDB_RESPONSE_PAGING_PARAM in (result := self._dynamodb_client.query(**query_params)):
            query_params[DDB_REQUEST_PAGING_PARAM] = result.get(DDB_RESPONSE_PAGING_PARAM)
            used_ami_ids.update({attr_dict.get("originalAmiId") for attr_dict in result.get("Items", [])})

        used_ami_ids.update({attr_dict.get("originalAmiId") for attr_dict in result.get("Items", [])})

        return used_ami_ids

    def _get_filter_expression(
        self,
        aws_account_ids: list[str] | None = None,
        is_recommended: bool | None = None,
        region: str | None = None,
        stage: str | None = None,
        status: str | None = None,
        version_name: str | None = None,
        statuses: list[version.VersionStatus] | None = None,
        original_ami_id_exists: bool | None = None,
    ) -> AttributeBase | None:
        filter_expression: AttributeBase | None = None
        account_id_condition = self._get_account_id_criteria(aws_account_ids)
        recommended_condition = self._get_is_recommended_criteria(is_recommended)
        region_condition = self._get_region_criteria(region)
        stage_condition = self._get_stage_criteria(stage)
        status_condition = self._get_status_criteria(status)
        version_name_contains_condition = self._get_version_name_contains_criteria(version_name)
        statuses_condition = self._get_statuses_criteria(statuses)
        original_ami_id_exists_condition = self._get_original_ami_id_exists_criteria(original_ami_id_exists)

        conditions = [
            account_id_condition,
            recommended_condition,
            region_condition,
            stage_condition,
            status_condition,
            version_name_contains_condition,
            statuses_condition,
            original_ami_id_exists_condition,
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

    def _get_status_criteria(
        self,
        status: str | None = None,
    ) -> AttributeBase | None:
        return Attr("status").eq(status) if status is not None else None

    def _get_version_id_criteria(self, version_id: str | None = None) -> ConditionBase:
        if version_id:
            return Key("SK").begins_with(f"{dynamo_db_repositories.DBPrefix.VERSION}#{version_id}#")
        else:
            return Key("SK").begins_with(f"{dynamo_db_repositories.DBPrefix.VERSION}#")

    def _get_version_name_begins_with_criteria(self, version_name_begins_with: str) -> AttributeBase | None:
        return Attr("versionName").begins_with(version_name_begins_with) if version_name_begins_with else None

    def _get_version_name_contains_criteria(self, version_name: str | None = None) -> AttributeBase | None:
        return Attr("versionName").contains(version_name) if version_name else None

    def _get_statuses_criteria(
        self,
        statuses: list[version.VersionStatus] | None = None,
    ) -> AttributeBase | None:
        return Attr("status").is_in(statuses) if statuses else None

    def _get_original_ami_id_exists_criteria(self, original_ami_id_exists: bool | None) -> AttributeBase | None:
        return Attr("originalAmiId").ne(None) if original_ami_id_exists else None
