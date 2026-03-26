from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import component_version_id_value_object
from app.packaging.domain.value_objects.shared import user_id_value_object
from app.shared.adapters.message_bus import command_bus


class UpdateRecipeVersionOnComponentUpdateCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionId: component_version_id_value_object.ComponentVersionIdValueObject
    lastUpdatedBy: user_id_value_object.UserIdValueObject
