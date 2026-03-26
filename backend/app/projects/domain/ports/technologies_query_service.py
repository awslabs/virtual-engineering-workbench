from abc import ABC, abstractmethod
from typing import List

from app.projects.domain.model import technology


class TechnologiesQueryService(ABC):
    @abstractmethod
    def list_technologies(self, project_id: str, page_size: int) -> List[technology.Technology]: ...
