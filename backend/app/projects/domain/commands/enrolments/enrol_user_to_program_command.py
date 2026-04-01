from typing import Optional

from pydantic import ConfigDict

from app.projects.domain.value_objects import (
    enrolment_id_value_object,
    project_id_value_object,
    source_system_value_object,
    user_email_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class EnrolUserToProgramCommand(command_bus.Command):
    project_id: project_id_value_object.ProjectIdValueObject
    user_id: user_id_value_object.UserIdValueObject
    user_email: user_email_value_object.UserEmailValueObject
    source_system: source_system_value_object.SourceSystemValueObject
    enrolment_id: Optional[enrolment_id_value_object.EnrolmentIdValueObject] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
