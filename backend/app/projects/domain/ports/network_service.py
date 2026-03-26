from abc import ABC, abstractmethod

from app.shared.adapters.boto.boto_provider import BotoProviderOptions


class NetworkService(ABC):
    @abstractmethod
    def get_vpc_id_by_tag(
        self,
        tag_name: str,
        tag_value: str,
        provider_options: BotoProviderOptions | None = None,
    ) -> str: ...

    @abstractmethod
    def get_vpcs_ids(
        self,
        provider_options: BotoProviderOptions | None = None,
    ) -> list[str]: ...

    def get_subnets_by_tag(
        self,
        tag_name: str,
        tag_value: str,
        vpc_id: str | None = None,
        provider_options: BotoProviderOptions | None = None,
    ) -> list[str]: ...
