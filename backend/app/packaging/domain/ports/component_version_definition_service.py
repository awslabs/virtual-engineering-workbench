from abc import ABC, abstractmethod
from typing import Union

from app.packaging.domain.model.component import component_version


class ComponentVersionDefinitionService(ABC):
    """Port for managing EC2 Image Builder component definitions.

    This service provides capabilities for component definition management
    including upload, retrieval, and presigned URL generation for S3-stored definitions.
    """

    @abstractmethod
    def get_component_version_definition(
        self, component_version: component_version.ComponentVersion
    ) -> Union[dict, str]: ...

    @abstractmethod
    def upload(
        self,
        component_id: str,
        component_version: str,
        component_definition: bytes,
    ) -> str: ...

    @abstractmethod
    def get_s3_presigned_url(self, s3_uri: str) -> str: ...
