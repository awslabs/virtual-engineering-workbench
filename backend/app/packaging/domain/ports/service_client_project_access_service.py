from abc import ABC, abstractmethod


class ServiceClientProjectAccessService(ABC):
    @abstractmethod
    def require_access(self, client_id: str, project_id: str) -> None: ...
