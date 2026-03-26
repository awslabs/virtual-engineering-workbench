from typing import Any, List

import boto3
from mypy_boto3_imagebuilder import client

from app.packaging.domain.ports import component_version_service
from app.shared.api import sts_api

SESSION_USER = "ProductPackagingProcess"


class Ec2ImageBuilderComponentService(component_version_service.ComponentVersionService):
    def __init__(
        self,
        admin_role: str,
        ami_factory_aws_account_id: str,
        region: str,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._ami_factory_aws_account_id = ami_factory_aws_account_id
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

            list_components_query_kwargs = {
                "filters": [
                    {"name": "name", "values": [name]},
                    {"name": "version", "values": [version]},
                ],
            }
            components = []
            response = imagebuilder_client.list_components(**list_components_query_kwargs)
            components.extend(response.get("componentVersionList", []))
            while "nextToken" in (response):
                list_components_query_kwargs["nextToken"] = response.get("nextToken")
                response = imagebuilder_client.list_components(**list_components_query_kwargs)
                components.extend(response.get("componentVersionList", []))
            # For a given component name and version, there can't be more than one
            if len(components) == 0:
                return None
            # ARN does not contain build number, only 1 build at a time will be there, so /1 can be appended
            return components[0].get("arn") + "/1"

    def create(
        self,
        name: str,
        version: str,
        s3_component_uri: str,
        platform: str,
        supported_os_versions: List[str] = [],
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

            response = imagebuilder_client.create_component(
                name=name,
                semanticVersion=version,
                description=description,
                platform=platform,
                supportedOsVersions=supported_os_versions,
                uri=s3_component_uri,
            )

            return response.get("componentBuildVersionArn")

    def delete(self, component_build_version_arn: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            imagebuilder_client = self.__get_imagebuilder_client(access_key_id, secret_access_key, session_token)

            imagebuilder_client.delete_component(
                componentBuildVersionArn=component_build_version_arn,
            )
