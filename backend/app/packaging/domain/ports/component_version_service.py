from abc import ABC, abstractmethod


class ComponentVersionService(ABC):
    @abstractmethod
    def get_build_arn(self, name: str, version: str) -> str | None: ...

    @abstractmethod
    def create(
        self,
        name: str,
        version: str,
        s3_component_uri: str,
        platform: str,
        supported_os_versions: list[str] = [],
        description: str = "",
    ) -> str: ...

    @abstractmethod
    def delete(self, component_build_version_arn: str) -> None: ...
