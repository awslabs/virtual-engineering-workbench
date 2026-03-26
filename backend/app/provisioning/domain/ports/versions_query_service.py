from abc import ABC, abstractmethod

from app.provisioning.domain.read_models import version


class VersionsQueryService(ABC):
    @abstractmethod
    def get_product_version_distributions(
        self,
        product_id: str,
        version_id: str | None = None,
        aws_account_ids: list[str] | None = None,
        is_recommended: bool | None = None,
        region: str | None = None,
        stage: version.VersionStage | None = None,
    ) -> list[version.Version]: ...

    @abstractmethod
    def get_by_provisioning_artifact_id(self, sc_provisioning_artifact_id: str) -> version.Version | None: ...

    @abstractmethod
    def get_product_version_distribution(
        self,
        product_id: str,
        version_id: str,
        aws_account_id: str,
    ) -> version.Version | None: ...
