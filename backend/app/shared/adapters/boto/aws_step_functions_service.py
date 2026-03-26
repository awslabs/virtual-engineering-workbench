from mypy_boto3_stepfunctions import client

from app.shared.adapters.boto import orchestration_service
from app.shared.adapters.boto.boto_provider import BotoProviderOptions, ProviderType


class AWSStepFunctionsService(orchestration_service.OrchestrationService):

    def __init__(
        self,
        sfn_provider: ProviderType[client.SFNClient],
    ):
        self.__sfn_provider = sfn_provider

    def send_callback_success(
        self,
        callback_token: str,
        result: dict = {},
        provider_options: BotoProviderOptions | None = None,
    ) -> None:

        sfn_client: client.SFNClient = self.__sfn_provider(provider_options)

        sfn_client.send_task_success(taskToken=callback_token, output=str(result) if result else "{}")

    def send_callback_failure(
        self,
        callback_token: str,
        error_type: str,
        error_message: str,
        provider_options: BotoProviderOptions | None = None,
    ) -> None:

        sfn_client: client.SFNClient = self.__sfn_provider(provider_options)

        sfn_client.send_task_failure(
            taskToken=callback_token,
            error=error_type,
            cause=error_message,
        )
