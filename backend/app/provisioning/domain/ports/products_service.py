from abc import ABC, abstractmethod

from app.provisioning.domain.model import (
    provisioned_product_details,
    provisioned_product_output,
    provisioning_parameter,
)


class ProductsService(ABC):
    @abstractmethod
    def provision_product(
        self,
        user_id: str,
        aws_account_id: str,
        sc_product_id: str,
        sc_provisioning_artifact_id: str,
        provisioning_parameters: list[provisioning_parameter.ProvisioningParameter],
        name: str,
        region: str,
        tags: list[dict[str, str]],
    ) -> str: ...

    @abstractmethod
    def update_product(
        self,
        user_id: str,
        aws_account_id: str,
        sc_provisioned_product_id: str,
        sc_product_id: str,
        sc_provisioning_artifact_id: str,
        provisioning_parameters: list[provisioning_parameter.ProvisioningParameter],
        region: str,
    ) -> str: ...

    @abstractmethod
    def deprovision_product(
        self,
        user_id: str,
        aws_account_id: str,
        provisioned_product_id: str,
        region: str,
    ) -> None: ...

    @abstractmethod
    def get_provisioned_product_outputs(
        self,
        provisioned_product_id: str,
        user_id: str,
        aws_account_id: str,
        region: str,
    ) -> list[provisioned_product_output.ProvisionedProductOutput]: ...

    @abstractmethod
    def get_provisioned_product_details(
        self, provisioned_product_id: str, user_id: str, aws_account_id: str, region: str
    ) -> provisioned_product_details.ProvisionedProductDetails | None: ...

    @abstractmethod
    def get_provisioned_product_supported_instance_type_param(
        self, provisioned_product_id: str, user_id: str, aws_account_id: str, region: str
    ) -> list[str] | None: ...

    @abstractmethod
    def has_provisioned_product_insufficient_capacity_error(
        self,
        provisioned_product_id: str,
        user_id: str,
        aws_account_id: str,
        region: str,
        provisioned_instance_type: str | None,
    ) -> bool: ...

    @abstractmethod
    def has_provisioned_product_missing_removal_signal_error(
        self,
        provisioned_product_id: str,
        user_id: str,
        aws_account_id: str,
        region: str,
    ) -> bool: ...
