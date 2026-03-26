from abc import ABC, abstractmethod

from app.publishing.domain.model import shared_ami


class SharedAMIsQueryService(ABC):
    @abstractmethod
    def get_shared_amis(self, original_ami_id: str) -> list[shared_ami.SharedAmi]: ...
