from abc import ABC, abstractmethod

from app.authorization.domain.read_models import project, project_assignment
from app.shared.adapters.boto import paging_utils


class ProjectsQueryService(ABC):
    @abstractmethod
    def get_user_assignments(self, user_id: str) -> list[project_assignment.Assignment]: ...

    @abstractmethod
    def get_projects(self, page: paging_utils.PageInfo) -> paging_utils.PagedResponse[project.Project]: ...

    @abstractmethod
    def get_project_assignments(
        self, project_id: str, page: paging_utils.PageInfo
    ) -> paging_utils.PagedResponse[project_assignment.Assignment]: ...
