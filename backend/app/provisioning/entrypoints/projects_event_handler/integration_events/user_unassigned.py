from typing import Literal

from pydantic import BaseModel, Field


class UserUnAssigned(BaseModel):
    message_type: Literal["unassign-user-request"] = Field("unassign-user-request", alias="messageType")
    user_id: str = Field(..., alias="userId")
    project_id: str = Field(..., alias="projectId")
