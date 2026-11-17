from abc import ABC, abstractmethod

from app.packaging.domain.read_models.marketplace_ami import MarketplaceAmi


class MarketplaceAmiService(ABC):
    @abstractmethod
    def list_marketplace_amis_by_product_code(self, product_code: str, region: str) -> list[MarketplaceAmi]: ...

    @abstractmethod
    def list_marketplace_amis_by_product_id(self, product_id: str, region: str) -> list[MarketplaceAmi]: ...

    @abstractmethod
    def get_regional_ami_ids(self, product_code: str, available_regions: list[str]) -> dict[str, str]: ...
