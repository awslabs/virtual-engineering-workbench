from abc import ABC, abstractmethod

from app.packaging.domain.read_models import marketplace_image


class MarketplaceImageService(ABC):
    @abstractmethod
    def list_images(self) -> list[marketplace_image.MarketplaceImage]: ...

    @abstractmethod
    def get_image(self, product_id: str) -> marketplace_image.MarketplaceImage | None: ...
