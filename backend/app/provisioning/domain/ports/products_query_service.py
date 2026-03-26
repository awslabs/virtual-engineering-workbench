from abc import ABC, abstractmethod
from typing import Optional

from app.provisioning.domain.read_models import product


class ProductsQueryService(ABC):
    @abstractmethod
    def get_products(
        self,
        project_id: str,
        product_type: Optional[product.ProductType] = None,
        available_stages: Optional[list[product.ProductStage]] = None,
    ) -> list[product.Product]: ...

    @abstractmethod
    def get_product(
        self,
        project_id: str,
        product_id: str,
    ) -> product.Product | None: ...
