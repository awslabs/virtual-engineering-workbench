from app.packaging.domain.ports import component_query_service
from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object


class ComponentDomainQueryService:
    def __init__(self, component_qry_srv: component_query_service.ComponentQueryService):
        self._component_qry_srv = component_qry_srv

    def get_components(self, project_id: project_id_value_object.ProjectIdValueObject):
        return self._component_qry_srv.get_components(project_id=project_id.value)

    def get_component(self, component_id: component_id_value_object.ComponentIdValueObject):
        return self._component_qry_srv.get_component(component_id=component_id.value)

    def get_component_project_associations(self, component_id: component_id_value_object.ComponentIdValueObject):
        return self._component_qry_srv.get_component_project_associations(component_id=component_id.value)
