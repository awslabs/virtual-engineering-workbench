from abc import ABC, abstractmethod
from typing import Dict


class NetworkingQueryService(ABC):
    @abstractmethod
    def get_network_ip_address_mapping(self) -> Dict: ...

    @abstractmethod
    def get_available_networks(self) -> list[str]: ...
