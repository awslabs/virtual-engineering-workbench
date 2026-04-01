from boto3.dynamodb.conditions import Attr, Key
from mypy_boto3_dynamodb import client

from app.packaging.adapters.repository.dynamo_entity_config import DBPrefix, PagingParams
from app.packaging.domain.model.image import image
from app.packaging.domain.ports import image_query_service


class DynamoDBImageQueryService(image_query_service.ImageQueryService):
    """Image DynamoDB repository query service."""

    def __init__(
        self,
        table_name: str,
        dynamodb_client: client.DynamoDBClient,
        gsi_custom_query_by_build_version_arn: str,
        gsi_custom_query_by_recipe_id_and_version: str,
        gsi_name_entities: str,
        gsi_name_image_upstream_id: str,
        default_page_size: int | None = None,
    ):
        self._table_name = table_name
        self._dynamodb_client = dynamodb_client
        self._gsi_custom_query_by_build_version_arn = gsi_custom_query_by_build_version_arn
        self._gsi_custom_query_by_recipe_id_and_version = gsi_custom_query_by_recipe_id_and_version
        self._gsi_name_entities = gsi_name_entities
        self._gsi_name_image_upstream_id = gsi_name_image_upstream_id
        self._default_page_size = default_page_size

    def get_images(self, project_id: str, exclude_status: image.ImageStatus | None = None) -> list[image.Image]:
        """Returns the list of all images for the given project."""

        images: list[image.Image] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("PK").eq(f"{DBPrefix.Project}#{project_id}")
            & Key("SK").begins_with(f"{DBPrefix.Image}#"),
        }
        if exclude_status:
            query_kwargs["FilterExpression"] = Attr("status").ne(exclude_status.value)

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            images.extend(result.get("Items", []))

        images.extend(result.get("Items", []))

        return [image.Image.model_validate(obj) for obj in images]

    def get_images_by_recipe_id_and_version_name(self, recipe_id: str, recipe_version_name: str) -> list[image.Image]:
        """Returns the list of all images for the given recipe id and version name."""

        images: list[image.Image] = []
        query_kwargs = {
            "TableName": self._table_name,
            "KeyConditionExpression": Key("QPK_RECIPE").eq(f"{DBPrefix.Recipe}#{recipe_id}")
            & Key("QSK_VERSION").eq(f"{DBPrefix.Version}#{recipe_version_name}"),
            "IndexName": self._gsi_custom_query_by_recipe_id_and_version,
        }

        if self._default_page_size:
            query_kwargs[PagingParams.PAGE_SIZE] = self._default_page_size

        while PagingParams.RESPONSE_PAGING in (result := self._dynamodb_client.query(**query_kwargs)):
            query_kwargs[PagingParams.REQUEST_PAGING] = result.get(PagingParams.RESPONSE_PAGING)
            images.extend(result.get("Items", []))

        images.extend(result.get("Items", []))

        return [image.Image.model_validate(obj) for obj in images]

    def get_image(self, project_id: str, image_id: str) -> image.Image | None:
        """Return image for given image id."""

        result = self._dynamodb_client.get_item(
            TableName=self._table_name,
            Key={
                "PK": f"{DBPrefix.Project}#{project_id}",
                "SK": f"{DBPrefix.Image}#{image_id}",
            },
        )

        if "Item" in result:
            return image.Image.model_validate(result["Item"])
        else:
            return None

    def get_image_by_image_build_version_arn(self, image_build_version_arn: str) -> image.Image | None:
        """Return image for given image build version ARN."""

        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("QPK_ARN").eq(f"{DBPrefix.Arn}#{image_build_version_arn}"),
            IndexName=self._gsi_custom_query_by_build_version_arn,
        )

        # Only 1 result is returned at a time, hence we don't paginate
        if result.get("Items", []):
            return image.Image.model_validate(result.get("Items", [])[0])
        else:
            return None

    def get_image_by_image_upstream_id(self, image_upstream_id: str) -> image.Image | None:
        """Return image for given image upstream id."""

        result = self._dynamodb_client.query(
            TableName=self._table_name,
            KeyConditionExpression=Key("imageUpstreamId").eq(image_upstream_id),
            IndexName=self._gsi_name_image_upstream_id,
        )

        # Only 1 result is returned at a time, hence we don't paginate
        if result.get("Items", []):
            return image.Image.model_validate(result["Items"][0])
        else:
            return None
