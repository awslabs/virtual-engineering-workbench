from abc import ABC, abstractmethod

from app.packaging.domain.read_models.received_license import ReceivedLicense


class MarketplaceLicenseService(ABC):
    @abstractmethod
    def list_received_licenses(self) -> list[ReceivedLicense]: ...
