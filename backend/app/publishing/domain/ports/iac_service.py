from abc import ABC, abstractmethod
from typing import Optional, Tuple

from app.publishing.domain.model import version


class IACService(ABC):
    @abstractmethod
    def validate_template(
        self, template_body: str = None, template_url: str = None
    ) -> Tuple[bool, Optional[list[version.VersionParameter]], Optional[str]]: ...
