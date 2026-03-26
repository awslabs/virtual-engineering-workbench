from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_name_value_object,
    component_version_yaml_definition_value_object,
)
from app.shared.adapters.message_bus import command_bus


class DeployComponentVersionCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionId: component_version_id_value_object.ComponentVersionIdValueObject
    componentVersionName: component_version_name_value_object.ComponentVersionNameValueObject
    componentVersionDescription: component_version_description_value_object.ComponentVersionDescriptionValueObject
    componentVersionYamlDefinition: (
        component_version_yaml_definition_value_object.ComponentVersionYamlDefinitionValueObject
    )
