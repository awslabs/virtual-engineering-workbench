from abc import ABC, abstractmethod


class PublishingQueryService(ABC):
    @abstractmethod
    def get_all_amis(self) -> list[str]: ...
