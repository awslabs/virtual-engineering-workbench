from functools import reduce
from typing import Optional

from boto3.dynamodb.conditions import Attr, Key
from mypy_boto3_dynamodb import client

from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.provisioning.domain.ports import products_query_service
from app.provisioning.domain.read_models import product


class DynamoDBProductsQueryService(products_query_service.ProductsQueryService):
    """DynamoDB Products repository query service"""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._default_page_size = default_page_size
        self._entity_config = dynamo_entity_config.EntityConfigurator(table_name=table_name)

    def get_products(
        self,
        project_id: str,
        product_type: Optional[product.ProductType] = None,
        available_stages: Optional[list[product.ProductStage]] = None,
    ) -> list[product.Product]:
        """Returns the list of all products for the given project."""

        products = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.PROJECT.value}#{project_id}")
            & Key("SK").begins_with(f"{DBPrefix.PRODUCT}#"),
        }
        done = False
        start_key = None

        if available_stages:
            filters = [Attr("availableStages").contains(stage) for stage in available_stages]
            query_kwargs["FilterExpression"] = reduce(lambda x, y: x | y, filters)

        if product_type:
            query_kwargs["FilterExpression"] = (
                query_kwargs["FilterExpression"] & Attr("productType").eq(product_type)
                if query_kwargs.get("FilterExpression")
                else Attr("productType").eq(product_type)
            )

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while not done:
            if start_key:
                query_kwargs[PagingParams.REQUEST_PAGING] = start_key
            result = self._dynamodb_client.query(**query_kwargs)

            start_key = result.get(PagingParams.RESPONSE_PAGING, None)
            done = start_key is None
            if result.get("Items"):
                products.extend([product.Product.model_validate(item) for item in result["Items"]])

        return products

    def get_product(
        self,
        project_id: str,
        product_id: str,
    ) -> product.Product | None:
        key = self._entity_config.get_config_for(product.ProductPrimaryKey, product.Product).primary_key_to_dict(
            product.ProductPrimaryKey(
                projectId=project_id,
                productId=product_id,
            )
        )

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key=key,
        )

        if "Item" in result:
            return product.Product.model_validate(result["Item"])

        return None
