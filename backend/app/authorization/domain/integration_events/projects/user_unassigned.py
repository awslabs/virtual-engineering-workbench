from pydantic import BaseModel, Field


class UserUnAssigned(BaseModel):
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
