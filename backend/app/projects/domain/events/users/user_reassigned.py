from typing import List

from pydantic import Field

from app.projects.domain.model.project_assignment import Role
from app.shared.adapters.message_bus import message_bus


class UserReAssigned(message_bus.Message):
    event_name: str = Field("UserReAssigned", alias="eventName", const=True)
    message_type: str = Field("reassign-user-request", alias="messageType", const=True)
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
    roles: List[Role] = Field(..., alias="roles")
