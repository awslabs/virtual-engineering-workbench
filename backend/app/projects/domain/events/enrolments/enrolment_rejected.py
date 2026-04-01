import typing
from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class EnrolmentRejected(message_bus.Message):
    event_name: Literal["EnrolmentRejected"] = Field("EnrolmentRejected", alias="eventName")
    program_id: str = Field(..., alias="programId")
    program_name: str = Field(..., alias="programName")
    user_id: str = Field(..., alias="userId")
    user_email: typing.Optional[str] = Field(
        ..., alias="userEmail"
    )  # Required but nullable: callers must explicitly pass this field, even if the value is None
    enrolment_id: str = Field(..., alias="enrolmentId")
    reason: str = Field(..., alias="reason")
