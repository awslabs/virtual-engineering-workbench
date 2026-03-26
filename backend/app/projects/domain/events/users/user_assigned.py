from typing import List

from pydantic import Field

from app.projects.domain.model.project_assignment import Role
from app.shared.adapters.message_bus import message_bus


class UserAssigned(message_bus.Message):
    event_name: str = Field("UserAssigned", alias="eventName", const=True)
    message_type: str = Field("assign-user-request", alias="messageType", const=True)
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
    roles: List[Role] = Field(..., alias="roles")
