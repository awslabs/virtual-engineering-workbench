from typing import List, Literal

from pydantic import Field

from app.projects.domain.model.project_assignment import Role
from app.shared.adapters.message_bus import message_bus


class UserAssigned(message_bus.Message):
    event_name: Literal["UserAssigned"] = Field("UserAssigned", alias="eventName")
    message_type: Literal["assign-user-request"] = Field("assign-user-request", alias="messageType")
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
    roles: List[Role] = Field(..., alias="roles")
