from abc import ABC, abstractmethod

from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement


class MarketplaceAgreementService(ABC):
    @abstractmethod
    def list_active_agreements(self) -> list[MarketplaceAgreement]: ...
