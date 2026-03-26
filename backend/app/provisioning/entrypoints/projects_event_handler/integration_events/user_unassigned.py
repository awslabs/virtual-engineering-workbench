from pydantic import BaseModel, Field


class UserUnAssigned(BaseModel):
    message_type: str = Field("unassign-user-request", alias="messageType", const=True)
    user_id: str = Field(..., alias="userId")
    project_id: str = Field(..., alias="projectId")
