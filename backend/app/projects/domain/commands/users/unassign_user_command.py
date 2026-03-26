from app.projects.domain.value_objects import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class UnAssignUserCommand(command_bus.Command):
    project_id: project_id_value_object.ProjectIdValueObject
    user_ids: list[user_id_value_object.UserIdValueObject]

    class Config:
        arbitrary_types_allowed = True
