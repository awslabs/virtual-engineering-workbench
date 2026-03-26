from abc import ABC, abstractmethod
from typing import Optional


class CatalogService(ABC):
    @abstractmethod
    def create_portfolio(self, region: str, portfolio_id: str, portfolio_name: str, portfolio_provider: str) -> str: ...

    @abstractmethod
    def share_portfolio(self, region: str, sc_portfolio_id: str, aws_account_id: str) -> None: ...

    @abstractmethod
    def accept_portfolio_share(self, region: str, sc_portfolio_id: str, aws_account_id: str) -> None: ...

    @abstractmethod
    def associate_role_with_portfolio(
        self,
        region: str,
        sc_portfolio_id: str,
        role_name: str,
        aws_account_id: Optional[str] = None,
    ) -> None: ...

    @abstractmethod
    def disassociate_role_from_portfolio(
        self,
        region: str,
        sc_portfolio_id: str,
        role_name: str,
        aws_account_id: Optional[str] = None,
    ) -> None: ...

    @abstractmethod
    def list_roles_for_portfolio(
        self,
        region: str,
        sc_portfolio_id: str,
        aws_account_id: Optional[str] = None,
    ) -> list[str]: ...

    @abstractmethod
    def create_provisioning_artifact(
        self, region: str, version_id: str, version_name: str, sc_product_id: str, description: str, template_path: str
    ) -> str: ...

    @abstractmethod
    def create_product(
        self,
        region: str,
        product_name: str,
        owner: str,
        product_description: str,
        version_id: str,
        version_name: str,
        version_description: str,
        template_path: str,
    ) -> tuple[str, str]: ...

    @abstractmethod
    def associate_product_with_portfolio(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> None: ...

    @abstractmethod
    def create_launch_constraint(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> None: ...

    @abstractmethod
    def create_notification_constraint(
        self,
        region: str,
        sc_portfolio_id: str,
        sc_product_id: str,
    ) -> None: ...

    @abstractmethod
    def create_resource_update_constraint(
        self,
        region: str,
        sc_portfolio_id: str,
        sc_product_id: str,
    ) -> None: ...

    @abstractmethod
    def delete_provisioning_artifact(
        self, region: str, sc_product_id: str, sc_provisioning_artifact_id: str
    ) -> None: ...

    @abstractmethod
    def update_provisioning_artifact_name(
        self, region, sc_product_id, sc_provisioning_artifact_id: str, new_name: str
    ) -> str: ...

    @abstractmethod
    def disassociate_product_from_portfolio(self, region: str, sc_portfolio_id: str, sc_product_id: str) -> None: ...

    @abstractmethod
    def delete_product(self, region: str, sc_product_id: str) -> None: ...
