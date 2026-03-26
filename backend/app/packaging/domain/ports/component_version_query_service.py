from abc import ABC, abstractmethod

from app.packaging.domain.model.component import component_version, component_version_summary


class ComponentVersionQueryService(ABC):
    @abstractmethod
    def get_latest_component_version_name(self, component_id: str) -> str | None: ...

    @abstractmethod
    def get_component_versions(self, component_id: str) -> list[component_version.ComponentVersion]: ...

    @abstractmethod
    def get_component_version(
        self, component_id: str, version_id: str
    ) -> component_version.ComponentVersion | None: ...

    @abstractmethod
    def get_all_components_versions(
        self, status: str, architecture: str, os: str, platform: str
    ) -> list[component_version_summary.ComponentVersionSummary]: ...
