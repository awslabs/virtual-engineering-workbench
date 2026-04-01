from typing import List, Literal

from pydantic import Field

from app.projects.domain.model.project_assignment import Role
from app.shared.adapters.message_bus import message_bus


class UserReAssigned(message_bus.Message):
    event_name: Literal["UserReAssigned"] = Field("UserReAssigned", alias="eventName")
    message_type: Literal["reassign-user-request"] = Field("reassign-user-request", alias="messageType")
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
    roles: List[Role] = Field(..., alias="roles")
