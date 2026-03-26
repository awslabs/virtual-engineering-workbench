from typing import Any

import boto3
from mypy_boto3_imagebuilder import client

from app.packaging.domain.ports import recipe_version_service
from app.shared.api import sts_api

SESSION_USER = "ProductPackagingProcess"


class Ec2ImageBuilderRecipeService(recipe_version_service.RecipeVersionService):
    def __init__(
        self,
        admin_role: str,
        ami_factory_aws_account_id: str,
        image_key_name: str,
        region: str,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._ami_factory_aws_account_id = ami_factory_aws_account_id
        self._image_key_name = image_key_name
        self._region = region
        self._boto_session = boto_session

    def __get_imagebuilder_client(
        self, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
    ) -> client.ImagebuilderClient:
        _imagebuilder_client: client.ImagebuilderClient = (
            self._boto_session.client(
                "imagebuilder",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
            if self._boto_session
            else boto3.client(
                "imagebuilder",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        )
        return _imagebuilder_client

    def get_build_arn(self, name: str, version: str) -> str | None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)

            list_recipes_query_kwargs = {"filters": [{"name": "name", "values": [name]}]}
            recipes = []
            response = imagebuilder_client.list_image_recipes(**list_recipes_query_kwargs)
            recipes.extend(response.get("imageRecipeSummaryList", []))
            while "nextToken" in response:
                list_recipes_query_kwargs["nextToken"] = response.get("nextToken")
                response = imagebuilder_client.list_image_recipes(**list_recipes_query_kwargs)
                recipes.extend(response.get("imageRecipeSummaryList", []))
            # Since it is not possible for filter for version, we need to check the ARNs
            for recipe in recipes:
                if recipe.get("arn").split("/")[-1] == version:
                    return recipe.get("arn")
            return None

    def create(
        self,
        name: str,
        version: str,
        component_arns: list[str],
        parent_image: str,
        volume_size: int,
        description: str = "",
    ) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()
            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)
            components = []
            for component_arn in component_arns:
                components.append({"componentArn": component_arn})
            response = imagebuilder_client.create_image_recipe(
                name=name,
                description=description,
                semanticVersion=version,
                components=components,
                parentImage=parent_image,
                blockDeviceMappings=[
                    {
                        "deviceName": "/dev/sda1",
                        "ebs": {
                            "encrypted": True,
                            "kmsKeyId": f"arn:aws:kms:{self._region}:{self._ami_factory_aws_account_id}:alias/{self._image_key_name}",
                            "volumeSize": volume_size,
                        },
                    }
                ],
            )
            return response.get("imageRecipeArn")

    def delete(self, recipe_version_arn: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)

            imagebuilder_client.delete_image_recipe(imageRecipeArn=recipe_version_arn)
