from abc import ABC, abstractmethod

from app.publishing.domain.model import version


class CatalogQueryService(ABC):
    @abstractmethod
    def does_portfolio_exist_in_sc(self, region: str, sc_portfolio_id: str) -> bool: ...

    @abstractmethod
    def get_sc_product_id(self, region: str, sc_product_name: str) -> str | None: ...

    @abstractmethod
    def get_sc_provisioning_artifact_id(self, region: str, sc_product_id: str, sc_version_name: str) -> str | None: ...

    @abstractmethod
    def get_launch_constraint_id(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> str | None: ...

    @abstractmethod
    def get_notification_constraint_id(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> str | None: ...

    @abstractmethod
    def get_resource_update_constraint_id(
        self, region: str, sc_portfolio_id: str, sc_product_id: str
    ) -> str | None: ...

    @abstractmethod
    def does_product_exist_in_sc(self, region: str, sc_product_id: str) -> bool: ...

    @abstractmethod
    def does_provisioning_artifact_exist_in_sc(
        self, region: str, sc_product_id: str, sc_provisioning_artifact_id: str
    ) -> bool: ...

    @abstractmethod
    def get_provisioning_artifact_count_in_sc(self, region: str, sc_product_id: str) -> int: ...

    @abstractmethod
    def get_provisioning_parameters(
        self, region: str, sc_product_id: str, sc_provisioning_artifact_id: str
    ) -> tuple[list[version.VersionParameter], dict[str, version.ProductVersionMetadataItem] | None]: ...
