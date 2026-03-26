import json

from mypy_boto3_lambda import client

from app.shared.adapters.boto import orchestration_service
from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType


class AWSDurableFunctionsService(orchestration_service.OrchestrationService):

    def __init__(
        self,
        lambda_provider: ProviderType[client.LambdaClient],
    ):
        self.__lambda_provider = lambda_provider

    def send_callback_success(
        self,
        callback_token: str,
        result: dict = {},
        provider_options: BotoProviderOptions | None = None,
    ) -> None:

        lambda_client: client.LambdaClient = self.__lambda_provider(provider_options)

        lambda_client.send_durable_execution_callback_success(
            CallbackId=callback_token,
            Result=json.dumps(result).encode("utf-8"),
        )

    def send_callback_failure(
        self,
        callback_token: str,
        error_type: str,
        error_message: str,
        provider_options: BotoProviderOptions | None = None,
    ) -> None:

        lambda_client: client.LambdaClient = self.__lambda_provider(provider_options)

        lambda_client.send_durable_execution_callback_failure(
            CallbackId=callback_token, Error={"ErrorMessage": error_message, "ErrorType": error_type}
        )
