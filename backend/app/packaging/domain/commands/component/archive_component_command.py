from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class ArchiveComponentCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    componentId: component_id_value_object.ComponentIdValueObject
    lastUpdatedBy: user_id_value_object.UserIdValueObject
