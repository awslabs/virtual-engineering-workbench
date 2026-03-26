import typing
from abc import ABC, abstractmethod

from app.publishing.domain.model import version


class VersionsQueryService(ABC):
    @abstractmethod
    def get_latest_version_name_and_id(
        self, product_id: str, version_name_begins_with: str = None
    ) -> typing.Tuple[str | None, str | None]: ...

    @abstractmethod
    def get_product_version_distributions(
        self,
        product_id: str,
        version_id: str | None = None,
        aws_account_ids: list[str] | None = None,
        is_recommended: bool | None = None,
        region: str | None = None,
        stage: version.VersionStage | None = None,
        statuses: list[version.VersionStatus] | None = None,
    ) -> list[version.Version]: ...

    @abstractmethod
    def get_distinct_number_of_versions(
        self, product_id: str, status: version.VersionStatus | None = None, version_name_filter: str = None
    ) -> int: ...

    @abstractmethod
    def get_product_version_distribution(
        self,
        product_id: str,
        version_id: str,
        aws_account_id: str,
    ) -> version.Version | None: ...

    @abstractmethod
    def get_all_versions(self, region: str | None = None) -> list[version.Version]: ...

    @abstractmethod
    def get_used_ami_ids_in_all_versions(self, region: str | None = None) -> set[str]: ...
