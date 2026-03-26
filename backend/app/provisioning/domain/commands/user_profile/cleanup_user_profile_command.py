from app.provisioning.domain.value_objects import user_id_value_object
from app.shared.adapters.message_bus import command_bus


class CleanUpUserProfileCommand(command_bus.Command):
    user_id: user_id_value_object.UserIdValueObject
