import base64
from typing import Any, Union

import boto3
import semver
import yaml
from mypy_boto3_s3 import client

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.model.component import component_version
from app.packaging.domain.ports import component_version_definition_service
from app.shared.api import sts_api

PRESIGN_URL_EXPIRATION_SECONDS = 60
SESSION_USER = "ProductPackagingProcess"


class AWSComponentDefinitionService(component_version_definition_service.ComponentVersionDefinitionService):
    def __init__(
        self,
        admin_role: str,
        ami_factory_aws_account_id: str,
        bucket_name: str,
        region: str,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._ami_factory_aws_account_id = ami_factory_aws_account_id
        self._bucket_name = bucket_name
        self._region = region
        self._boto_session = boto_session

    def __get_s3_client(
        self, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
    ) -> client.S3Client:
        _s3_client: client.S3Client = (
            self._boto_session.client(
                "s3",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
            if self._boto_session
            else boto3.client(
                "s3",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        )
        return _s3_client

    def __get_component_version_definition_bytes(self, component_version: component_version.ComponentVersion) -> bytes:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id,
            self._region,
            self._admin_role,
            SESSION_USER,
            self._boto_session,
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            s3_client = self.__get_s3_client(access_key_id, secret_access_key, session_token)

            s3_uri = component_version.componentVersionS3Uri

            if not s3_uri:
                raise adapter_exception.AdapterException(
                    f"YAML definition for component version with ID "
                    f"{component_version.componentVersionId} is not available."
                )

            bucket_name, object_key = s3_uri.split("//")[1].split("/", 1)

            response = s3_client.get_object(
                Bucket=bucket_name,
                Key=object_key,
            )
            yaml_definition = response["Body"].read()

            return yaml_definition

    def get_component_version_definition(
        self, component_version: component_version.ComponentVersion
    ) -> Union[dict, str]:

        yaml_definition_bytes = self.__get_component_version_definition_bytes(component_version=component_version)
        yaml_definition_obj = yaml.safe_load(yaml_definition_bytes)
        yaml_definition_b64 = base64.b64encode(yaml_definition_bytes).decode("utf-8")

        return yaml_definition_obj, yaml_definition_b64

    def upload(
        self,
        component_id: str,
        component_version: str,
        component_definition: bytes,
    ) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id,
            self._region,
            self._admin_role,
            SESSION_USER,
            self._boto_session,
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            s3_client = self.__get_s3_client(access_key_id, secret_access_key, session_token)
            key_prefix = f"{component_id}/{semver.Version.parse(component_version).finalize_version()}/component.yaml"
            pre_release = semver.Version.parse(component_version).prerelease

            s3_client.put_object(
                Bucket=self._bucket_name,
                Key=key_prefix,
                Body=component_definition,
                Tagging=f"release-candidate={pre_release}" if pre_release else "",
            )

            return f"s3://{self._bucket_name}/{key_prefix}"

    def get_s3_presigned_url(self, s3_uri: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id,
            self._region,
            self._admin_role,
            SESSION_USER,
            self._boto_session,
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            s3_client = self.__get_s3_client(access_key_id, secret_access_key, session_token)

            bucket_name, object_key = s3_uri.split("//")[1].split("/", 1)
            response = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": object_key},
                ExpiresIn=PRESIGN_URL_EXPIRATION_SECONDS,
            )

            return response
