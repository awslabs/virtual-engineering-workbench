from boto3.dynamodb.conditions import Key
from mypy_boto3_dynamodb import service_resource

from app.packaging.adapters.repository import dynamo_entity_config
from app.shared.adapters.unit_of_work_v2 import dynamodb_repo_config


def migrations_config(gsi_entities: str):

    def image_add_image_source_pipeline(table: service_resource.Table):
        """001.Image_Add_ImageSource_Pipeline

        Stamps imageSource=PIPELINE on all existing Image records that lack the attribute.
        Also removes imageUpstreamId when it was stored as NULL (DynamoDB NULL type).
        """
        cli = table.meta.client
        paginator = cli.get_paginator("query")

        pages = paginator.paginate(
            TableName=table.table_name,
            IndexName=gsi_entities,
            KeyConditionExpression=Key(dynamodb_repo_config.ATTRIBUTE_NAME_ENTITY).eq(
                dynamo_entity_config.DBPrefix.Image.value
            ),
        )

        for page in pages:
            for item in page.get("Items", []):
                if "imageSource" in item:
                    continue
                has_null_upstream = item.get("imageUpstreamId") is None
                update_expr = (
                    "SET imageSource = :source REMOVE imageUpstreamId"
                    if has_null_upstream
                    else "SET imageSource = :source"
                )
                cli.update_item(
                    TableName=table.table_name,
                    Key={"PK": item["PK"], "SK": item["SK"]},
                    UpdateExpression=update_expr,
                    ExpressionAttributeValues={":source": "PIPELINE"},
                )

    return [
        (
            "001.Image_Add_ImageSource_Pipeline",
            image_add_image_source_pipeline,
        ),
    ]
