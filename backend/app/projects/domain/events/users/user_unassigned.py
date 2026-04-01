from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class UserUnAssigned(message_bus.Message):
    event_name: Literal["UserUnAssigned"] = Field("UserUnAssigned", alias="eventName")
    message_type: Literal["unassign-user-request"] = Field("unassign-user-request", alias="messageType")
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
