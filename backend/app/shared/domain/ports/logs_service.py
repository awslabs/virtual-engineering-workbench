from abc import ABC, abstractmethod
from typing import Optional

from app.shared.adapters.boto.boto_provider import BotoProviderOptions


class LogsService(ABC):
    @abstractmethod
    def describe_log_groups(
        self,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> list[dict]: ...

    @abstractmethod
    def put_retention_policy(
        self,
        log_group_name: str,
        retention_days: int,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...
