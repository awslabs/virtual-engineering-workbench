from abc import ABC, abstractmethod
from typing import Optional

from app.shared.adapters.boto.boto_provider import BotoProviderOptions


class DNSService(ABC):
    @abstractmethod
    def associate_vpc_with_zone(
        self,
        vpc_id: str,
        vpc_region: str,
        zone_id: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...

    @abstractmethod
    def create_dns_record(
        self,
        name: str,
        ttl: int,
        type: str,
        value: str,
        zone_id: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> None: ...

    @abstractmethod
    def create_private_zone(
        self,
        comment: str,
        dns_name: str,
        vpc_id: str,
        vpc_region: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> str: ...

    @abstractmethod
    def get_zone_id(
        self,
        dns_name: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> Optional[str]: ...

    @abstractmethod
    def is_vpc_associated_with_zone(
        self,
        dns_name: str,
        vpc_id: str,
        vpc_region: str,
        provider_options: Optional[BotoProviderOptions] = None,
    ) -> bool: ...
