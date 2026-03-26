import enum
from typing import List, Optional

from pydantic import Field, validator

from app.projects.domain.model import user
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class Role(enum.StrEnum):
    ADMIN = "ADMIN"
    PLATFORM_USER = "PLATFORM_USER"
    BETA_USER = "BETA_USER"
    POWER_USER = "POWER_USER"
    PROGRAM_OWNER = "PROGRAM_OWNER"
    PRODUCT_CONTRIBUTOR = "PRODUCT_CONTRIBUTOR"


class AssignmentPrimaryKey(unit_of_work.PrimaryKey):
    userId: str = Field(..., title="UserId")
    projectId: str = Field(..., title="ProjectId")


class Assignment(unit_of_work.Entity):
    userId: str = Field(..., title="UserId")
    projectId: str = Field(..., title="ProjectId")
    roles: List[Role] = Field(..., title="Roles")
    userEmail: Optional[str] = Field(None, title="UserEmail")
    activeDirectoryGroups: list[user.ActiveDirectoryGroup] = Field([], title="ActiveDirectoryGroups")
    activeDirectoryGroupStatus: user.UserADStatus = Field(user.UserADStatus.UNKNOWN, title="ActiveDirectoryGroupStatus")

    @validator("roles", each_item=True, pre=True)
    def roles_upper_case(cls, v):
        return v.upper()
