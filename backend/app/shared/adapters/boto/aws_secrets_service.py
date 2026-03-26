from typing import Optional

from mypy_boto3_secretsmanager import client

from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType
from app.shared.adapters.exceptions import adapter_exception
from app.shared.domain.ports import secret_service


class AWSSecretsService(secret_service.SecretsService):
    def __init__(
        self,
        secretsmanager_provider: ProviderType[client.SecretsManagerClient],
    ):
        self._provider = secretsmanager_provider

    def create_secret(
        self,
        secret_name: str,
        secret_value: str,
        description: Optional[str] = None,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        secretsmanager_client = self._provider(provider_options)

        args = {
            "Name": secret_name,
            "SecretString": secret_value,
        }
        if description:
            args["Description"] = description

        secretsmanager_client.create_secret(**args)

    def describe_secret(
        self,
        secret_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> str:
        secretsmanager_client = self._provider(provider_options)

        try:
            response = secretsmanager_client.describe_secret(SecretId=secret_name)

            return response["Name"], response["Description"]
        except secretsmanager_client.exceptions.ResourceNotFoundException:
            raise adapter_exception.AdapterException(f'Unable to get secret "{secret_name}".')

    def get_secret_value(
        self,
        secret_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> str:
        secretsmanager_client = self._provider(provider_options)

        try:
            response = secretsmanager_client.get_secret_value(SecretId=secret_name)

            return response["SecretString"]
        except secretsmanager_client.exceptions.ResourceNotFoundException:
            raise adapter_exception.AdapterException(f'Unable to get secret "{secret_name}".')

    def get_secrets_ids_by_path(
        self,
        path: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> list[str]:
        secrets_ids = list()
        secretsmanager_client = self._provider(provider_options)
        paginator = secretsmanager_client.get_paginator("list_secrets")

        for page in paginator.paginate():
            for secret in page["SecretList"]:
                secret_id = secret.get("Name")

                if secret_id.startswith(path):
                    secrets_ids.append(secret_id)

        return secrets_ids

    def update_secret(
        self,
        secret_name: str,
        secret_value: str,
        description: Optional[str] = None,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        secretsmanager_client = self._provider(provider_options)

        args = {
            "SecretId": secret_name,
            "SecretString": secret_value,
        }
        if description:
            args["Description"] = description

        secretsmanager_client.update_secret(**args)

    def upsert_secret(
        self,
        secret_name: str,
        secret_value: str,
        description: Optional[str] = None,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        secretsmanager_client = self._provider(provider_options)

        args = {
            "Name": secret_name,
            "SecretString": secret_value,
        }
        if description:
            args["Description"] = description

        try:
            secretsmanager_client.create_secret(**args)
        except secretsmanager_client.exceptions.ResourceExistsException:
            del args["Name"]
            args["SecretId"] = secret_name

            secretsmanager_client.update_secret(**args)
