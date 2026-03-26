import typing

from pydantic import Field

from app.projects.domain.model.project_assignment import Role
from app.shared.adapters.message_bus import message_bus


class EnrolmentApproved(message_bus.Message):
    event_name: str = Field("EnrolmentApproved", alias="eventName", const=True)
    program_id: str = Field(..., alias="programId")
    program_name: str = Field(..., alias="programName")
    user_id: str = Field(..., alias="userId")
    user_email: typing.Optional[str] = Field(..., alias="userEmail")
    enrolment_id: str = Field(..., alias="enrolmentId")
    roles: list[Role] = Field(..., alias="roles")
