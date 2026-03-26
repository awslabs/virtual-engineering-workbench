import logging
import os
import tempfile
from typing import Any

import boto3
from mypy_boto3_s3 import client

from app.publishing.domain.ports import template_service
from app.shared.api import sts_api

SESSION_USER = "ProductPublishingProcess"


class S3FileService(template_service.TemplateService):
    def __init__(
        self,
        admin_role: str,
        tools_aws_account_id: str,
        region: str,
        bucket_name: str,
        logger: logging.Logger,
        boto_session: Any = None,
    ):
        self._admin_role = admin_role
        self._tools_aws_account_id = tools_aws_account_id
        self._region = region
        self._bucket_name = bucket_name
        self._logger = logger
        self._boto_session = boto_session

    def get_template(self, template_path: str, download_directory: str = tempfile.gettempdir()) -> str:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create S3 API instance cross-account
            s3_client: client.S3Client = (
                self._boto_session.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            destination_path = os.path.join(download_directory, os.path.basename(template_path))

            # Call the S3 api
            s3_client.download_file(Bucket=self._bucket_name, Key=template_path, Filename=destination_path)

            return destination_path

    def put_template(self, template_path: str, content: bytes) -> None:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create S3 API instance cross-account
            s3_client: client.S3Client = (
                self._boto_session.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the S3 api
            s3_client.put_object(Bucket=self._bucket_name, Key=template_path, Body=content)

    def does_template_exist(self, template_path: str) -> bool:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create S3 API instance cross-account
            s3_client: client.S3Client = (
                self._boto_session.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the S3 head object api
            try:
                s3_client.head_object(Bucket=self._bucket_name, Key=template_path)
            except s3_client.exceptions.ClientError as e:
                if e.response.get("Error", {}).get("Code") == "404":
                    return False
                raise

            return True

    def get_object(self, object_path: str) -> str:
        # Get STS temp credentials
        with sts_api.STSAPI(
            self._tools_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            # Create S3 API instance cross-account
            s3_client: client.S3Client = (
                self._boto_session.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
                if self._boto_session
                else boto3.client(
                    "s3",
                    region_name=self._region,
                    aws_access_key_id=access_key_id,
                    aws_secret_access_key=secret_access_key,
                    aws_session_token=session_token,
                )
            )

            # Call the S3 api
            try:
                response = s3_client.get_object(Bucket=self._bucket_name, Key=object_path)
                return response["Body"].read().decode("utf-8")
            except s3_client.exceptions.ClientError as e:
                self._logger.error(f"Error getting object '{object_path}' from bucket '{self._bucket_name}': {e}")
                raise
