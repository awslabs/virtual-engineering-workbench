from typing import List

from app.projects.domain.value_objects import user_id_value_object
from app.shared.adapters.message_bus import command_bus


class RejectEnrolmentsCommand(command_bus.Command):
    project_id: str
    enrolment_ids: List[str]
    reason: str
    rejecter_id: user_id_value_object.UserIdValueObject

    class Config:
        arbitrary_types_allowed = True
