import typing
from abc import ABC, abstractmethod

from app.provisioning.domain.read_models import project, project_account, project_assignment


class ProjectsQueryService(ABC):
    @abstractmethod
    def get_aws_accounts_by_status(
        self,
        project_id: str,
        statuses: list,
        account_type: typing.Optional[str] = None,
        stage: typing.Optional[str] = None,
    ) -> list[project_account.ProjectAccount]: ...

    @abstractmethod
    def get_aws_account_by_id(
        self,
        project_id: str,
        account_id: str,
    ) -> typing.Optional[project_account.ProjectAccount]: ...

    @abstractmethod
    def get_projects(self) -> list[project.Project]: ...

    @abstractmethod
    def get_user_assignments_count(self, user_id: str) -> int: ...

    @abstractmethod
    def get_project(self, project_id: str) -> project.Project: ...

    @abstractmethod
    def get_project_assignment(self, project_id: str, user_id: str) -> project_assignment.ProjectAssignment | None: ...
