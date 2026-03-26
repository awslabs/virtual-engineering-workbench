from app.packaging.domain.value_objects.component import (
    component_description_value_object,
    component_id_value_object,
    component_name_value_object,
    component_system_configuration_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class CreateComponentCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    componentId: component_id_value_object.ComponentIdValueObject
    componentDescription: component_description_value_object.ComponentDescriptionValueObject
    componentName: component_name_value_object.ComponentNameValueObject
    componentSystemConfiguration: component_system_configuration_value_object.ComponentSystemConfigurationValueObject
    createdBy: user_id_value_object.UserIdValueObject
