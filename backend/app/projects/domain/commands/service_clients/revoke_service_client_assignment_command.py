from pydantic import ConfigDict

from app.projects.domain.value_objects import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class RevokeServiceClientAssignmentCommand(command_bus.Command):
    project_id: project_id_value_object.ProjectIdValueObject
    client_id: str
    revoked_by: str

    model_config = ConfigDict(arbitrary_types_allowed=True)
