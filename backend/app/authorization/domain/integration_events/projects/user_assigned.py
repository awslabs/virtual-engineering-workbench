from typing import List

from pydantic import BaseModel, Field

from app.authorization.domain.read_models import project_assignment


class UserAssigned(BaseModel):
    userId: str = Field(..., alias="userId")
    projectId: str = Field(..., alias="projectId")
    roles: List[project_assignment.Role] = Field(..., alias="roles")
    groupMemberships: list[project_assignment.Group] = Field([], alias="groupMemberships")
