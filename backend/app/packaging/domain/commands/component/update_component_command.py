from app.packaging.domain.value_objects.component import (
    component_description_value_object,
    component_id_value_object,
)
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.message_bus import command_bus


class UpdateComponentCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentDescription: component_description_value_object.ComponentDescriptionValueObject
    lastUpdatedBy: user_id_value_object.UserIdValueObject
