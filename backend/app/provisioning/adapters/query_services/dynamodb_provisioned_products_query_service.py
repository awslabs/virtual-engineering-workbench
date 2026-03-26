from typing import Iterator, List, Optional, Tuple

from boto3.dynamodb.conditions import Attr, ConditionBase, Key
from mypy_boto3_dynamodb import client

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.adapters.repository.dynamo_entity_config import REPLICATION_FACTOR, DBPrefix, PagingParams
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.ports import provisioned_products_query_service


class DynamoDBProvisionedProductsQueryService(provisioned_products_query_service.ProvisionedProductsQueryService):
    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_inverted_primary_key: str,
        gsi_custom_query_by_service_catalog_id: str,
        gsi_custom_query_by_user_id: str,
        gsi_custom_query_all: str,
        gsi_custom_query_by_product_id: str,
        gsi_custom_query_by_project_id: str,
        gsi_custom_query_by_status: str,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_inverted_primary_key = gsi_inverted_primary_key
        self._gsi_custom_query_by_service_catalog_id = gsi_custom_query_by_service_catalog_id
        self._gsi_custom_query_by_user_id = gsi_custom_query_by_user_id
        self._gsi_custom_query_all = gsi_custom_query_all
        self._gsi_custom_query_by_product_id = gsi_custom_query_by_product_id
        self._gsi_custom_query_by_project_id = gsi_custom_query_by_project_id
        self._default_page_size = default_page_size
        self._gsi_custom_query_by_status = gsi_custom_query_by_status

    def get_by_id(self, provisioned_product_id: str) -> provisioned_product.ProvisionedProduct | None:
        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("SK").eq(f"{DBPrefix.PROVISIONED_PRODUCT.value}#{provisioned_product_id}"),
            Limit=1,
            IndexName=self._gsi_inverted_primary_key,
        )

        if len(result.get("Items")) > 1:
            raise adapter_exception.AdapterException(
                f"More than 1 provisioned product found for {provisioned_product_id}"
            )

        if result.get("Items"):
            return provisioned_product.ProvisionedProduct.parse_obj(result["Items"][0])

        return None

    def get_by_sc_provisioned_product_id(
        self, sc_provisioned_product_id: str
    ) -> provisioned_product.ProvisionedProduct | None:
        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("QPK_1").eq(
                f"{DBPrefix.SC_PROVISIONED_PRODUCT.value}#{sc_provisioned_product_id}"
            ),
            Limit=1,
            IndexName=self._gsi_custom_query_by_service_catalog_id,
        )

        if len(result.get("Items")) > 1:
            raise adapter_exception.AdapterException(
                f"More than 1 provisioned product found for {sc_provisioned_product_id}"
            )

        if result.get("Items"):
            return provisioned_product.ProvisionedProduct.parse_obj(result["Items"][0])

        return None

    def get_provisioned_products_by_user_id(
        self,
        user_id: str,
        project_id: str,
        exclude_status: list[product_status.ProductStatus] | None = None,
        stage: provisioned_product.ProvisionedProductStage | None = None,
        product_id: str | None = None,
        provisioned_product_type: provisioned_product.ProvisionedProductType | None = None,
    ) -> List[provisioned_product.ProvisionedProduct]:
        provisioned_products = []
        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_custom_query_by_user_id,
            "KeyConditionExpression": Key("GSI_PK").eq(f"{DBPrefix.USER.value}#{user_id}")
            & Key("GSI_SK").begins_with(f"{DBPrefix.PROVISIONED_PRODUCT}#{project_id}"),
        }
        done = False
        start_key = None

        filter_expression: ConditionBase | None = None

        filter_conditions = [
            (
                Attr("status").is_in([s for s in product_status.ProductStatus if s not in exclude_status])
                if exclude_status
                else None
            ),
            Attr("stage").eq(stage) if stage else None,
            Attr("productId").eq(product_id) if product_id else None,
            Attr("provisionedProductType").eq(provisioned_product_type) if provisioned_product_type else None,
        ]

        for filter_condition in (c for c in filter_conditions if c):
            filter_expression = filter_expression & filter_condition if filter_expression else filter_condition

        if filter_expression:
            query_kwargs["FilterExpression"] = filter_expression

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while not done:
            if start_key:
                query_kwargs[PagingParams.REQUEST_PAGING] = start_key
            result = self._dynamodb_client.query(**query_kwargs)

            start_key = result.get(PagingParams.RESPONSE_PAGING, None)
            done = start_key is None
            if result.get("Items"):
                provisioned_products.extend(
                    [provisioned_product.ProvisionedProduct.parse_obj(item) for item in result["Items"]]
                )

        return provisioned_products

    def get_provisioned_product(
        self,
        project_id: str,
        provisioned_product_id: str,
    ) -> Optional[provisioned_product.ProvisionedProduct]:
        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("PK").eq(f"{DBPrefix.PROJECT.value}#{project_id}")
            & Key("SK").eq(f"{DBPrefix.PROVISIONED_PRODUCT.value}#{provisioned_product_id}"),
            Limit=1,
        )

        if len(result.get("Items")) > 1:
            raise adapter_exception.AdapterException(
                f"More than 1 provisioned product found for {provisioned_product_id}"
            )

        if result.get("Items"):
            return provisioned_product.ProvisionedProduct.parse_obj(result["Items"][0])

        return None

    def get_all_cross_projects_provisioned_products(
        self, exclude_terminated=False, start_key=None, page_size=None
    ) -> Tuple[List[provisioned_product.ProvisionedProduct], Optional[dict]]:
        """
        Scan all provisioned products across all projects
        """
        scan_kwargs = {
            "TableName": self._table_name,
            "Limit": page_size if page_size else self._default_page_size,
            "FilterExpression": Key("PK").begins_with(f"{DBPrefix.PROJECT}#")
            & Key("SK").begins_with(f"{DBPrefix.PROVISIONED_PRODUCT}#"),
        }
        if exclude_terminated:
            scan_kwargs["FilterExpression"] = scan_kwargs["FilterExpression"] & Attr("status").ne(
                product_status.ProductStatus.Terminated.value
            )

        if start_key:
            scan_kwargs[PagingParams.REQUEST_PAGING] = start_key

        result = self._dynamodb_client.scan(**scan_kwargs)
        start_key = result.get(PagingParams.RESPONSE_PAGING, None)
        return [provisioned_product.ProvisionedProduct.parse_obj(item) for item in result.get("Items", [])], start_key

    def get_all_provisioned_products(
        self,
        exclude_terminated: bool = False,
        exclude_running: bool = False,
        status: product_status.ProductStatus = None,
    ) -> Iterator[provisioned_product.ProvisionedProduct]:
        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_custom_query_all,
        }
        if exclude_terminated:
            query_kwargs["FilterExpression"] = Attr("status").ne(product_status.ProductStatus.Terminated.value)

        if exclude_running:
            query_kwargs["FilterExpression"] = (
                query_kwargs["FilterExpression"] & Attr("status").ne(product_status.ProductStatus.Running.value)
                if query_kwargs.get("FilterExpression")
                else Attr("status").ne(product_status.ProductStatus.Running.value)
            )

        if status:
            query_kwargs["FilterExpression"] = (
                query_kwargs["FilterExpression"] & Attr("status").eq(status)
                if query_kwargs.get("FilterExpression")
                else Attr("status").eq(status)
            )

        for i in range(REPLICATION_FACTOR):
            query_kwargs["KeyConditionExpression"] = Key("QPK_2").eq(f"{DBPrefix.PROVISIONED_PRODUCT.value}#PART#{i}")
            query_kwargs.pop(PagingParams.REQUEST_PAGING, None)

            done = False
            start_key = None

            while not done:
                if start_key:
                    query_kwargs[PagingParams.REQUEST_PAGING] = start_key

                result = self._dynamodb_client.query(**query_kwargs)

                start_key = result.get(PagingParams.RESPONSE_PAGING, None)
                done = start_key is None

                for item in result.get("Items", []):
                    yield provisioned_product.ProvisionedProduct.parse_obj(item)

    def get_all_provisioned_products_by_status(
        self,
        status: product_status.ProductStatus,
    ) -> Iterator[provisioned_product.ProvisionedProduct]:
        paginator = self._dynamodb_client.get_paginator("query")
        pages = paginator.paginate(
            TableName=self._table_name,
            IndexName=self._gsi_custom_query_by_status,
            KeyConditionExpression=Key("QPK_4").eq(f"{DBPrefix.PROVISIONED_PRODUCT}#{status}")
            & Key("SK").begins_with(f"{DBPrefix.PROVISIONED_PRODUCT}#"),
        )

        for page in pages:
            for item in page.get("Items", []):
                yield provisioned_product.ProvisionedProduct.parse_obj(item)

    def get_provisioned_products_by_project_id_paginated(
        self,
        project_id: str,
        page_size: int,
        paging_key: Optional[dict],
        status: Optional[product_status.ProductStatus] = None,
        stage: Optional[provisioned_product.ProvisionedProductStage] = None,
        product_name: Optional[str] = None,
        version_name: Optional[str] | None = None,
        owner: Optional[str] | None = None,
        provisioned_product_type: Optional[provisioned_product.ProvisionedProductType] = None,
        experimental: Optional[bool] = None,
    ) -> Tuple[List[provisioned_product.ProvisionedProduct], Optional[dict]]:
        if not page_size:
            page_size = self._default_page_size
        provisioned_products = []
        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_custom_query_by_project_id,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.PROJECT.value}#{project_id}")
            & Key("QSK_3").begins_with(f"{DBPrefix.PROVISIONED_PRODUCT}#{DBPrefix.ACTIVE}#"),
        }
        filter_expression: ConditionBase | None = None

        filter_conditions = [
            Attr("status").eq(status) if status else None,
            Attr("stage").eq(stage) if stage else None,
            Attr("productName").eq(product_name) if product_name else None,
            Attr("provisionedProductType").eq(provisioned_product_type) if provisioned_product_type else None,
            Attr("experimental").eq(experimental) if experimental else None,
            Attr("userId").eq(owner) if owner else None,
            Attr("versionName").eq(version_name) if version_name else None,
        ]

        for filter_condition in (c for c in filter_conditions if c):
            filter_expression = filter_expression & filter_condition if filter_expression else filter_condition

        if filter_expression:
            query_kwargs["FilterExpression"] = filter_expression

        done = None
        start_key = paging_key
        while not done:
            if start_key:
                query_kwargs[PagingParams.REQUEST_PAGING] = start_key

            result = self._dynamodb_client.query(**query_kwargs)
            pending_items = page_size - len(provisioned_products)
            if len(provisioned_products) + result.get("Count") >= page_size:
                current_page_items = result.get("Items")[:pending_items]
                last_evaluated_item = current_page_items[-1]
                start_key = self.__build_exclusive_start_key(last_evaluated_item)
                provisioned_products.extend(
                    [provisioned_product.ProvisionedProduct.parse_obj(item) for item in current_page_items]
                )
                done = True
            else:
                provisioned_products.extend(
                    [provisioned_product.ProvisionedProduct.parse_obj(item) for item in result.get("Items")]
                )
                start_key = result.get(PagingParams.RESPONSE_PAGING, None)
                done = start_key is None

        return provisioned_products, start_key

    def __build_exclusive_start_key(self, last_evaluated_item: dict):
        return {"PK": last_evaluated_item["PK"], "SK": last_evaluated_item["SK"], "QSK_3": last_evaluated_item["QSK_3"]}

    def get_provisioned_products_by_project_id(
        self,
        project_id: str,
        exclude_status: list[product_status.ProductStatus] | None = None,
        stage: provisioned_product.ProvisionedProductStage | None = None,
        product_id: str | None = None,
        provisioned_product_type: provisioned_product.ProvisionedProductType | None = None,
        experimental: bool | None = None,
    ) -> list[provisioned_product.ProvisionedProduct]:
        provisioned_products = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.PROJECT.value}#{project_id}")
            & Key("SK").begins_with(f"{DBPrefix.PROVISIONED_PRODUCT}#"),
        }
        done = False
        start_key = None

        filter_expression: ConditionBase | None = None

        filter_conditions = [
            (
                Attr("status").is_in([s for s in product_status.ProductStatus if s not in exclude_status])
                if exclude_status
                else None
            ),
            Attr("stage").eq(stage) if stage else None,
            Attr("productId").eq(product_id) if product_id else None,
            Attr("provisionedProductType").eq(provisioned_product_type) if provisioned_product_type else None,
            Attr("experimental").eq(experimental) if experimental else None,
        ]

        for filter_condition in (c for c in filter_conditions if c):
            filter_expression = filter_expression & filter_condition if filter_expression else filter_condition

        if filter_expression:
            query_kwargs["FilterExpression"] = filter_expression

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while not done:
            if start_key:
                query_kwargs[PagingParams.REQUEST_PAGING] = start_key
            result = self._dynamodb_client.query(**query_kwargs)

            start_key = result.get(PagingParams.RESPONSE_PAGING, None)
            done = start_key is None
            if result.get("Items"):
                provisioned_products.extend(
                    [provisioned_product.ProvisionedProduct.parse_obj(item) for item in result["Items"]]
                )

        return provisioned_products

    def get_all_provisioned_products_by_product_id(
        self, product_id: str, region: str | None = None, stage: str | None = None, version_id: str | None = None
    ) -> Iterator[provisioned_product.ProvisionedProduct]:

        if region and not stage:
            raise adapter_exception.AdapterException("stage parameter must also be provided when region is provided")

        query_args = [
            DBPrefix.PROVISIONED_PRODUCT,
            DBPrefix.ACTIVE,
            stage,
            region,
        ]

        sort_key_condition = "#".join(a for a in query_args if a)

        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_custom_query_by_product_id,
            "KeyConditionExpression": Key("QPK_3").eq(f"{DBPrefix.PRODUCT}#{product_id}")
            & Key("QSK_3").begins_with(f"{sort_key_condition}#"),
        }

        if version_id:
            query_kwargs["FilterExpression"] = Attr("versionId").eq(version_id)

        done = False
        start_key = None

        while not done:
            if start_key:
                query_kwargs[PagingParams.REQUEST_PAGING] = start_key

            result = self._dynamodb_client.query(**query_kwargs)

            start_key = result.get(PagingParams.RESPONSE_PAGING, None)
            done = start_key is None

            for item in result.get("Items", []):
                yield provisioned_product.ProvisionedProduct.parse_obj(item)

    def get_active_provisioned_products_by_project_id(
        self,
        project_id: str,
        provisioned_product_type: provisioned_product.ProvisionedProductType | None = None,
    ) -> list[provisioned_product.ProvisionedProduct]:
        provisioned_products = []
        query_kwargs = {
            "TableName": self._table_name,
            "IndexName": self._gsi_custom_query_by_project_id,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.PROJECT.value}#{project_id}")
            & Key("QSK_3").begins_with(f"{DBPrefix.PROVISIONED_PRODUCT}#{DBPrefix.ACTIVE}#"),
        }
        done = False
        start_key = None

        filter_expression: ConditionBase | None = None

        filter_conditions = [
            Attr("provisionedProductType").eq(provisioned_product_type) if provisioned_product_type else None,
        ]

        for filter_condition in (c for c in filter_conditions if c):
            filter_expression = filter_expression & filter_condition if filter_expression else filter_condition

        if filter_expression:
            query_kwargs["FilterExpression"] = filter_expression

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while not done:
            if start_key:
                query_kwargs[PagingParams.REQUEST_PAGING] = start_key
            result = self._dynamodb_client.query(**query_kwargs)

            start_key = result.get(PagingParams.RESPONSE_PAGING, None)
            done = start_key is None
            if result.get("Items"):
                provisioned_products.extend(
                    [provisioned_product.ProvisionedProduct.parse_obj(item) for item in result["Items"]]
                )

        return provisioned_products
