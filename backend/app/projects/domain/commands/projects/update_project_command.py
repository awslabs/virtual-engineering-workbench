from typing import Optional

from pydantic import ConfigDict

from app.projects.domain.value_objects import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class UpdateProjectCommand(command_bus.Command):
    id: project_id_value_object.ProjectIdValueObject
    name: str
    description: Optional[str] = None
    isActive: bool
    model_config = ConfigDict(arbitrary_types_allowed=True)
