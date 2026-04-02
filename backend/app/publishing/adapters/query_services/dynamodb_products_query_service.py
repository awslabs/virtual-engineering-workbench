from functools import reduce
from typing import Optional

from boto3.dynamodb.conditions import Attr, Key
from mypy_boto3_dynamodb import client

from app.publishing.adapters.exceptions import adapter_exception
from app.publishing.adapters.services.dynamo_db_repositories import DBPrefix
from app.publishing.domain.model import product
from app.publishing.domain.ports import products_query_service


class DynamoDBProductsQueryService(products_query_service.ProductsQueryService):
    """Products DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_name_entities: str,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_name_entities = gsi_name_entities

    def get_products(
        self,
        project_id: str,
        available_stages: Optional[list[product.ProductStage]] = None,
        status: Optional[product.ProductStatus] = None,
        product_type: product.ProductType = None,
    ) -> list[product.Product]:
        """Returns the list of all products for the given project."""

        products = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.PROJECT.value}#{project_id}")
            & Key("SK").begins_with(f"{DBPrefix.PRODUCT.value}#"),
        }
        done = False
        start_key = None

        if available_stages:
            filters = [Attr("availableStages").contains(stage) for stage in available_stages]
            query_kwargs["FilterExpression"] = reduce(lambda x, y: x | y, filters)

        if status:
            query_kwargs["FilterExpression"] = (
                query_kwargs["FilterExpression"] & Attr("status").eq(status)
                if query_kwargs.get("FilterExpression")
                else Attr("status").eq(status)
            )

        if product_type:
            query_kwargs["FilterExpression"] = (
                query_kwargs["FilterExpression"] & Attr("productType").eq(product_type)
                if query_kwargs.get("FilterExpression")
                else Attr("productType").eq(product_type)
            )

        while not done:
            if start_key:
                query_kwargs["ExclusiveStartKey"] = start_key
            result = self._dynamodb_client.query(**query_kwargs)

            start_key = result.get("LastEvaluatedKey", None)
            done = start_key is None
            if result.get("Items"):
                products.extend([product.Product.model_validate(item) for item in result["Items"]])

        return products

    def get_product(self, project_id: str, product_id: str) -> product.Product:
        """Return product for given project and product id."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.PROJECT.value}#{project_id}",
                "SK": f"{DBPrefix.PRODUCT.value}#{product_id}",
            },
        )

        if result.get("Item"):
            return product.Product.model_validate(result["Item"])

        raise adapter_exception.AdapterException(f"Product with id {product_id} not found.")
