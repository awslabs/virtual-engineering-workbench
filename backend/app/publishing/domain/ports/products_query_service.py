from abc import ABC, abstractmethod
from typing import Optional

from app.publishing.domain.model import product


class ProductsQueryService(ABC):
    @abstractmethod
    def get_products(
        self,
        project_id: str,
        available_stages: Optional[list[product.ProductStage]] = None,
        status: Optional[product.ProductStatus] = None,
        product_type: product.ProductType = None,
    ) -> list[product.Product]: ...

    @abstractmethod
    def get_product(self, project_id: str, product_id: str) -> product.Product: ...
