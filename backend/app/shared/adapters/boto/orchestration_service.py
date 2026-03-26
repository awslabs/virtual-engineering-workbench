from abc import ABC, abstractmethod

from app.shared.adapters.boto.boto_provider import BotoProviderOptions


class OrchestrationService(ABC):

    @abstractmethod
    def send_callback_success(
        self,
        callback_token: str,
        result: dict = {},
        provider_options: BotoProviderOptions | None = None,
    ) -> None: ...

    @abstractmethod
    def send_callback_failure(
        self,
        callback_token: str,
        error_type: str,
        error_message: str,
        provider_options: BotoProviderOptions | None = None,
    ) -> None: ...
