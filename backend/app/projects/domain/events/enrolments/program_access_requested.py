from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProgramAccessRequested(message_bus.Message):
    event_name: str = Field("ProgramAccessRequested", alias="eventName", const=True)
    message_type: str = Field("enrol-user-request", alias="messageType", const=True)
    program_id: str = Field(..., alias="programId")
    program_name: str = Field(..., alias="programName")
    user_id: str = Field(..., alias="userId")
    user_email: str = Field(..., alias="userEmail")
    reference_id: str = Field(..., alias="referenceId")
    source_system: str = Field(..., alias="sourceSystem")
