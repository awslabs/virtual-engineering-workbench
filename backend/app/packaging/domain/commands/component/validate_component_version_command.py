from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import component_version_yaml_definition_value_object
from app.shared.adapters.message_bus import command_bus


class ValidateComponentVersionCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionYamlDefinition: (
        component_version_yaml_definition_value_object.ComponentVersionYamlDefinitionValueObject
    )
