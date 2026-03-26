from abc import ABC, abstractmethod

from app.provisioning.domain.read_models import version


class PublishingQueryService(ABC):
    @abstractmethod
    def get_available_product_versions(
        self,
        product_id: str,
    ) -> list[version.Version]: ...

    def get_version(
        self,
        product_id: str,
        version_id: str,
        account_id: str,
    ) -> version.Version | None: ...
