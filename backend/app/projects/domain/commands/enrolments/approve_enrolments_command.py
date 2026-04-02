from typing import List

from pydantic import ConfigDict

from app.projects.domain.value_objects import user_id_value_object
from app.shared.adapters.message_bus import command_bus


class ApproveEnrolmentsCommand(command_bus.Command):
    project_id: str
    enrolment_ids: List[str]
    approver_id: user_id_value_object.UserIdValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
