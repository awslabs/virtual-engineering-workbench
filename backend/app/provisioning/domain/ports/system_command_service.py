from abc import ABC, abstractmethod

from app.provisioning.domain.model import additional_configuration


class SystemCommandService(ABC):
    @abstractmethod
    def run_document(
        self,
        aws_account_id: str,
        region: str,
        user_id: str,
        provisioned_product_configuration_type: additional_configuration.ProvisionedProductConfigurationTypeEnum,
        instance_id: str,
        parameters: list[additional_configuration.AdditionalConfigurationParameter],
    ) -> str | None: ...

    @abstractmethod
    def get_run_status(
        self, aws_account_id: str, region: str, user_id: str, instance_id: str, run_id: str
    ) -> tuple[additional_configuration.AdditionalConfigurationRunStatus, str]: ...

    @abstractmethod
    def is_instance_ready(self, aws_account_id: str, region: str, user_id: str, instance_id: str) -> bool: ...
