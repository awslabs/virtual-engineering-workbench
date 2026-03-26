import typing

from mypy_boto3_secretsmanager import client as sm_client
from mypy_boto3_ssm import client

from app.provisioning.adapters.exceptions import adapter_exception
from app.provisioning.domain.ports import parameter_service


class AWSParameterService(parameter_service.ParameterService):
    def __init__(
        self,
        ssm_boto_client_provider: typing.Callable[[str, str, str], client.SSMClient],
        sm_boto_client_provider: typing.Callable[[str, str, str], sm_client.SecretsManagerClient],
    ):
        self._ssm_boto_client_provider = ssm_boto_client_provider
        self._sm_boto_client_provider = sm_boto_client_provider

    def get_parameter_value(
        self,
        parameter_name: str,
        aws_account_id: str,
        region: str,
        user_id: str,
    ) -> str | None:
        ssm_client = self._ssm_boto_client_provider(aws_account_id, region, user_id)

        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=True)

        if not response or not response.get("Parameter", None):
            raise adapter_exception.AdapterException(
                f"Unable to get parameter {parameter_name} in aws account {aws_account_id}"
            )

        return str(response["Parameter"]["Value"])

    def get_secret_value(self, secret_name: str, aws_account_id: str, region: str, user_id: str) -> str | None:
        sm_client = self._sm_boto_client_provider(aws_account_id, region, user_id)

        response = sm_client.get_secret_value(SecretId=secret_name)

        if not response or not response.get("SecretString", None):
            raise adapter_exception.AdapterException(
                f"Unable to get secret {secret_name} in aws account {aws_account_id}"
            )

        return str(response["SecretString"])
