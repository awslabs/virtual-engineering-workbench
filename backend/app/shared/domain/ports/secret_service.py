from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.shared.adapters.boto.boto_provider import BotoProviderOptions


class SecretsService(ABC):
    @abstractmethod
    def create_secret(
        self,
        secret_name: str,
        secret_value: str,
        description: Optional[str] = None,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...

    @abstractmethod
    def describe_secret(
        self,
        secret_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> tuple[str, str]: ...

    @abstractmethod
    def get_secret_value(
        self,
        secret_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> str: ...

    @abstractmethod
    def get_secrets_ids_by_path(
        self,
        path: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> list[str]: ...

    @abstractmethod
    def update_secret(
        self,
        secret_name: str,
        secret_value: str | Dict[str, Any],
        description: Optional[str] = None,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...

    @abstractmethod
    def upsert_secret(
        self,
        secret_name: str,
        secret_value: str | Dict[str, Any],
        description: Optional[str] = None,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...
