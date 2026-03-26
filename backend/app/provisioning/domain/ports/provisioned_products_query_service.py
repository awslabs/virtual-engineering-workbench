from abc import ABC, abstractmethod
from typing import Iterator, List, Optional, Tuple

from app.provisioning.domain.model import product_status, provisioned_product


class ProvisionedProductsQueryService(ABC):
    @abstractmethod
    def get_by_id(self, provisioned_product_id: str) -> provisioned_product.ProvisionedProduct | None: ...

    @abstractmethod
    def get_by_sc_provisioned_product_id(
        self, sc_provisioned_product_id: str
    ) -> provisioned_product.ProvisionedProduct | None: ...

    @abstractmethod
    def get_provisioned_products_by_user_id(
        self,
        user_id: str,
        project_id: str,
        exclude_status: list[product_status.ProductStatus] | None = None,
        stage: provisioned_product.ProvisionedProductStage | None = None,
        product_id: str | None = None,
        provisioned_product_type: provisioned_product.ProvisionedProductType | None = None,
    ) -> List[provisioned_product.ProvisionedProduct]: ...

    @abstractmethod
    def get_provisioned_product(
        self,
        project_id: str,
        provisioned_product_id: str,
    ) -> provisioned_product.ProvisionedProduct: ...

    @abstractmethod
    def get_provisioned_products_by_project_id(
        self,
        project_id: str,
        exclude_status: list[product_status.ProductStatus] | None = None,
        stage: provisioned_product.ProvisionedProductStage | None = None,
        product_id: str | None = None,
        provisioned_product_type: provisioned_product.ProvisionedProductType | None = None,
        experimental: bool | None = None,
    ) -> list[provisioned_product.ProvisionedProduct]: ...

    @abstractmethod
    def get_all_provisioned_products(
        self,
        exclude_terminated: bool = False,
        exclude_running: bool = False,
        status: product_status.ProductStatus = None,
    ) -> Iterator[provisioned_product.ProvisionedProduct]: ...

    @abstractmethod
    def get_all_provisioned_products_by_status(
        self,
        status: product_status.ProductStatus,
    ) -> Iterator[provisioned_product.ProvisionedProduct]: ...

    @abstractmethod
    def get_all_cross_projects_provisioned_products(
        self, exclude_terminated=False, start_key=None, page_size=None
    ) -> Tuple[List[provisioned_product.ProvisionedProduct], Optional[dict]]: ...

    @abstractmethod
    def get_all_provisioned_products_by_product_id(
        self, product_id: str, region: str | None = None, stage: str | None = None, version_id: str | None = None
    ) -> Iterator[provisioned_product.ProvisionedProduct]: ...

    @abstractmethod
    def get_active_provisioned_products_by_project_id(
        self,
        project_id: str,
        provisioned_product_type: provisioned_product.ProvisionedProductType | None = None,
    ) -> list[provisioned_product.ProvisionedProduct]: ...

    @abstractmethod
    def get_provisioned_products_by_project_id_paginated(
        self,
        project_id: str,
        page_size: int,
        paging_key: Optional[dict],
        status: Optional[product_status.ProductStatus] = None,
        stage: Optional[provisioned_product.ProvisionedProductStage] = None,
        product_name: Optional[str] = None,
        version_name: Optional[str] | None = None,
        owner: Optional[str] | None = None,
        provisioned_product_type: Optional[provisioned_product.ProvisionedProductType] = None,
        experimental: Optional[bool] = None,
    ) -> Tuple[List[provisioned_product.ProvisionedProduct], Optional[dict]]: ...
