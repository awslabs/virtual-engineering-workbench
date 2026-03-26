from abc import ABC, abstractmethod

from app.packaging.domain.model.component import mandatory_components_list


class MandatoryComponentsListQueryService(ABC):
    @abstractmethod
    def get_mandatory_components_list(
        self, platform: str, os: str, architecture: str
    ) -> mandatory_components_list.MandatoryComponentsList: ...

    @abstractmethod
    def get_mandatory_components_lists(self) -> list[mandatory_components_list.MandatoryComponentsList]: ...
