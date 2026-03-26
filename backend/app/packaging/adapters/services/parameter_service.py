from typing import Any

import boto3
from mypy_boto3_ssm import client

from app.packaging.domain.ports import parameter_service
from app.shared.api import sts_api

SESSION_USER = "ProductPackagingProcess"


class ParameterService(parameter_service.ParameterDefinitionService):
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

    def __get_ssm_client(
        self, aws_access_key_id: str, aws_secret_access_key: str, aws_session_token: str
    ) -> client.SSMClient:
        _ssm_client: client.SSMClient = (
            self._boto_session.client(
                "ssm",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
            if self._boto_session
            else boto3.client(
                "ssm",
                region_name=self._region,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                aws_session_token=aws_session_token,
            )
        )
        return _ssm_client

    def get_parameter_value(self, parameter_name: str):
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()

            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)
            return ssm_client.get_parameter(Name=parameter_name).get("Parameter").get("Value")

    def get_parameter_value_from_path_with_decryption(self, parameter_path: str) -> str:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()
            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)
            return ssm_client.get_parameter(Name=parameter_path, WithDecryption=True).get("Parameter").get("Value")

    def create_parameter(self, parameter_name: str, parameter_value: str, parameter_type: str = "String") -> dict:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()
            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)
            return ssm_client.put_parameter(
                Name=parameter_name, Value=parameter_value, Type=parameter_type, Overwrite=True
            )

    def delete(self, parameter_name: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()
            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)
            ssm_client.delete_parameter(Name=parameter_name)

    def delete_by_path(self, parameter_path: str) -> None:
        with sts_api.STSAPI(
            self._ami_factory_aws_account_id, self._region, self._admin_role, SESSION_USER, self._boto_session
        ) as sts:
            (
                access_key_id,
                secret_access_key,
                session_token,
            ) = sts.get_temp_creds()
            ssm_client = self.__get_ssm_client(access_key_id, secret_access_key, session_token)
            ssm_client.delete_parameter(Name=parameter_path)
