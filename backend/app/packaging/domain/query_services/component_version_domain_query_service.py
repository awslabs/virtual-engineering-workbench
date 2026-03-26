from app.packaging.domain.ports import (
    component_query_service,
    component_version_definition_service,
    component_version_query_service,
)
from app.packaging.domain.value_objects.component import (
    component_id_value_object,
    component_platform_value_object,
    component_supported_architecture_value_object,
    component_supported_os_version_value_object,
)
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
    component_version_status_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object


class ComponentVersionDomainQueryService:
    def __init__(
        self,
        component_qry_srv: component_query_service.ComponentQueryService,
        component_version_qry_srv: component_version_query_service.ComponentVersionQueryService,
        component_version_definition_srv: component_version_definition_service.ComponentVersionDefinitionService,
    ):
        self._component_qry_srv = component_qry_srv
        self._component_version_qry_srv = component_version_qry_srv
        self._component_version_definition_srv = component_version_definition_srv

    def get_latest_component_version_name(self, component_id: component_id_value_object.ComponentIdValueObject):
        return self._component_version_qry_srv.get_latest_component_version_name(component_id=component_id.value)

    def get_component_versions(self, component_id: component_id_value_object.ComponentIdValueObject):
        return self._component_version_qry_srv.get_component_versions(component_id=component_id.value)

    def get_component_version(
        self,
        component_id: component_id_value_object.ComponentIdValueObject,
        version_id: component_version_id_value_object.ComponentVersionIdValueObject,
    ):
        component_version = self._component_version_qry_srv.get_component_version(
            component_id=component_id.value, version_id=version_id.value
        )
        yaml_definition_obj, yaml_definition_b64 = (
            self._component_version_definition_srv.get_component_version_definition(component_version)
        )
        return component_version, yaml_definition_obj, yaml_definition_b64

    def get_all_components_versions(
        self,
        architecture: component_supported_architecture_value_object.ComponentSupportedArchitectureValueObject,
        os: component_supported_os_version_value_object.ComponentSupportedOsVersionValueObject,
        platform: component_platform_value_object.ComponentPlatformValueObject,
        statuses: list[component_version_status_value_object.ComponentVersionStatusValueObject],
        project_id: project_id_value_object.ProjectIdValueObject = None,
    ):
        component_versions = list()

        for status in statuses:
            component_versions.extend(
                self._component_version_qry_srv.get_all_components_versions(
                    status=status.value, architecture=architecture.value, os=os.value, platform=platform.value
                )
            )

        if project_id:
            project_components = self._component_qry_srv.get_components(project_id=project_id.value)
            project_component_ids = [component.componentId for component in project_components]
            component_versions = [
                component_version
                for component_version in component_versions
                if component_version.componentId in project_component_ids
            ]

        return component_versions
