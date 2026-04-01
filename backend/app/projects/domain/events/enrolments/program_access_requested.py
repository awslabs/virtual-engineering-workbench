from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProgramAccessRequested(message_bus.Message):
    event_name: Literal["ProgramAccessRequested"] = Field("ProgramAccessRequested", alias="eventName")
    message_type: Literal["enrol-user-request"] = Field("enrol-user-request", alias="messageType")
    program_id: str = Field(..., alias="programId")
    program_name: str = Field(..., alias="programName")
    user_id: str = Field(..., alias="userId")
    user_email: str = Field(..., alias="userEmail")
    reference_id: str = Field(..., alias="referenceId")
    source_system: str = Field(..., alias="sourceSystem")
