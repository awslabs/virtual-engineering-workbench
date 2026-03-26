import typing
from abc import ABC, abstractmethod

from app.projects.domain.model import project, project_account, project_assignment, user
from app.shared.adapters.boto import paging_utils


class ProjectsQueryService(ABC):
    @abstractmethod
    def list_projects(
        self, page_size: int, next_token: typing.Any, user_id: str | None
    ) -> tuple[list[project.Project], typing.Any, list[project_assignment.Assignment]]: ...

    @abstractmethod
    def list_projects_by_user(
        self, user_id: str, page_size: int, next_token: typing.Any
    ) -> tuple[list[project.Project], typing.Any, list[project_assignment.Assignment]]: ...

    @abstractmethod
    def list_project_accounts(
        self,
        project_id: str,
        account_type: str | None = None,
        stage: str | None = None,
        technology_id: str | None = None,
    ) -> list[project_account.ProjectAccount]: ...

    @abstractmethod
    def list_project_accounts_by_aws_account(self, aws_account_id: str) -> list[project_account.ProjectAccount]: ...

    @abstractmethod
    def get_project_account_by_id(self, project_id: str, account_id: str) -> project_account.ProjectAccount | None: ...

    @abstractmethod
    def get_project_by_id(self, id: str) -> project.Project | None: ...

    @abstractmethod
    def list_users_by_project(self, project_id: str) -> list[project_assignment.Assignment]: ...

    @abstractmethod
    def list_users_by_project_paged(
        self, project_id: str, page: paging_utils.PageInfo
    ) -> paging_utils.PagedResponse[project_assignment.Assignment]: ...

    @abstractmethod
    def get_user_assignment(self, project_id: str, user_id: str) -> project_assignment.Assignment: ...

    @abstractmethod
    def list_all_accounts(
        self,
        page_size: int,
        next_token: typing.Any,
        account_type: str | None = None,
        stage: str | None = None,
        technology_id: str | None = None,
    ) -> tuple[list[project_account.ProjectAccount], typing.Any]: ...

    @abstractmethod
    def get_user(self, user_id: str) -> user.User | None: ...

    @abstractmethod
    def get_all_users(self, page_size: int, next_token: typing.Any) -> tuple[list[user.User], typing.Any]: ...
