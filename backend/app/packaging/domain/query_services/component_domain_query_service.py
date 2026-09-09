from aws_lambda_powertools.event_handler.exceptions import NotFoundError

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

    def require_component_in_project(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        component_id: component_id_value_object.ComponentIdValueObject,
    ) -> None:
        """Raise when the component is not associated with the given project.

        A component is shared with a project through a component project association, so the project
        the caller was authorized for must hold an association with the component it addresses.
        """

        if not self._component_qry_srv.is_component_in_project(
            project_id=project_id.value, component_id=component_id.value
        ):
            raise NotFoundError(f"Component {component_id.value} not found in project {project_id.value}.")
