from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_role_value_object
from app.shared.adapters.message_bus import command_bus


class ShareComponentCommand(command_bus.Command):
    projectIds: list[project_id_value_object.ProjectIdValueObject]
    componentId: component_id_value_object.ComponentIdValueObject
    userRoles: list[user_role_value_object.UserRoleValueObject]
