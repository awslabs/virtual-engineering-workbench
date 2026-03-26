from typing import List, Optional

from mypy_boto3_ssm import client

from app.shared.adapters.boto import parameter_service_v2
from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType
from app.shared.adapters.exceptions import adapter_exception


class AWSParameterService(parameter_service_v2.ParameterService):
    def __init__(
        self,
        ssm_provider: ProviderType[client.SSMClient],
    ):
        self._provider = ssm_provider

    def get_parameter_value(
        self,
        parameter_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> str | None:
        ssm_client = self._provider(provider_options)

        try:
            response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
            return str(response["Parameter"]["Value"])
        except ssm_client.exceptions.ParameterNotFound:
            raise adapter_exception.AdapterException(f'Unable to get parameter "{parameter_name}"')

    def get_list_parameter_value(
        self,
        parameter_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> List[str]:
        ssm_client = self._provider(provider_options)

        try:
            response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)
            return str(response["Parameter"]["Value"]).split(",")

        except ssm_client.exceptions.ParameterNotFound:
            raise adapter_exception.AdapterException(f'Unable to get parameter "{parameter_name}"')

    def get_parameters_by_path(
        self,
        path: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> dict[str, str]:
        ssm_client = self._provider(provider_options)

        paginator = ssm_client.get_paginator("get_parameters_by_path")

        parameters = {}

        for page in paginator.paginate(Path=path, Recursive=True, WithDecryption=True):
            parameters.update({p.get("Name"): p.get("Value") for p in page.get("Parameters", [])})

        return parameters

    def create_string_parameter(
        self,
        parameter_name: str,
        parameter_value: str,
        is_overwrite: bool = False,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        ssm_client = self._provider(provider_options)
        ssm_client.put_parameter(Name=parameter_name, Value=parameter_value, Type="String", Overwrite=is_overwrite)

    def delete_parameter(
        self,
        parameter_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None:
        ssm_client = self._provider(provider_options)
        ssm_client.delete_parameter(Name=parameter_name)
