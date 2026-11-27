from abc import ABC, abstractmethod


class MarketplaceOfferService(ABC):
    @abstractmethod
    def list_supported_instance_types(self, product_id: str) -> list[str]:
        """Instance types the product's offers price, i.e. the ones its AMIs launch on.

        Returns an empty list when they cannot be determined (no access, no usage-based terms).
        """
        ...
