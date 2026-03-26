from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple

from app.projects.domain.model import enrolment


class EnrolmentQueryService(ABC):
    @abstractmethod
    def get_enrolment_for_user(self, user_id: str, project_id: str) -> Optional[enrolment.Enrolment]: ...

    @abstractmethod
    def get_enrolment_by_id(self, enrolment_id: str, project_id: str) -> Optional[enrolment.Enrolment]: ...

    @abstractmethod
    def list_enrolments_by_project(
        self, project_id: str, page_size: int, next_token: Any, status: Optional[str] = None
    ) -> Tuple[List[enrolment.Enrolment], Any]: ...

    @abstractmethod
    def list_enrolments_by_user(
        self,
        user_id: str,
        page_size: int,
        next_token: Any,
        status: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Tuple[List[enrolment.Enrolment], Any]: ...
