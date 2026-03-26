from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class UserUnAssigned(message_bus.Message):
    event_name: str = Field("UserUnAssigned", alias="eventName", const=True)
    message_type: str = Field("unassign-user-request", alias="messageType", const=True)
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
