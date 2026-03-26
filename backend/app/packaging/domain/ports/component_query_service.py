from abc import ABC, abstractmethod

from app.packaging.domain.model.component import component, component_project_association


class ComponentQueryService(ABC):
    @abstractmethod
    def get_components(self, project_id: str) -> list[component.Component]: ...

    @abstractmethod
    def get_component(self, component_id: str) -> component.Component | None: ...

    @abstractmethod
    def get_component_project_associations(
        self, component_id: str
    ) -> list[component_project_association.ComponentProjectAssociation]: ...
