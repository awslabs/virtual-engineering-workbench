from typing import Optional

from app.projects.domain.value_objects import project_id_value_object, tech_id_value_object
from app.shared.adapters.message_bus import command_bus


class UpdateTechnologyCommand(command_bus.Command):
    id: tech_id_value_object.TechIdValueObject
    name: str
    description: Optional[str]
    project_id: project_id_value_object.ProjectIdValueObject

    class Config:
        arbitrary_types_allowed = True
