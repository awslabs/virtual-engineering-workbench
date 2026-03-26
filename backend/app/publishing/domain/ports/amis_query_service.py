from abc import ABC, abstractmethod

from app.publishing.domain.read_models import ami


class AMIsQueryService(ABC):
    @abstractmethod
    def get_amis(self, project_id: str) -> list[ami.Ami]: ...

    @abstractmethod
    def get_ami(self, ami_id: str) -> ami.Ami: ...
