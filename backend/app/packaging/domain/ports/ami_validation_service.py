from abc import ABC, abstractmethod

from app.packaging.domain.read_models.ami_description import AmiDescription


class AmiValidationService(ABC):
    @abstractmethod
    def describe_image(self, ami_id: str) -> AmiDescription: ...

    @abstractmethod
    def describe_marketplace_image(self, ami_id: str) -> AmiDescription: ...

    @abstractmethod
    def list_available_amis(self) -> list[AmiDescription]: ...

    @abstractmethod
    def validate_marketplace_product_code(self, ami_id: str, expected_product_code: str) -> bool: ...
