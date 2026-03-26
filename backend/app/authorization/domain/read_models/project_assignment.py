import enum
from enum import StrEnum
from typing import List, Optional

from pydantic import Field, validator

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class Role(StrEnum):
    ADMIN = "ADMIN"
    PLATFORM_USER = "PLATFORM_USER"
    BETA_USER = "BETA_USER"
    POWER_USER = "POWER_USER"
    PROGRAM_OWNER = "PROGRAM_OWNER"
    PRODUCT_CONTRIBUTOR = "PRODUCT_CONTRIBUTOR"


class Group(enum.StrEnum):
    VEW_USERS = "VEW_USERS"
    HIL_USERS = "HIL_USERS"
    VVPL_USERS = "VVPL_USERS"


class AssignmentPrimaryKey(unit_of_work.PrimaryKey):
    userId: str = Field(..., title="UserId")
    projectId: str = Field(..., title="ProjectId")


class Assignment(unit_of_work.Entity):
    userId: str = Field(..., title="UserId")
    projectId: str = Field(..., title="ProjectId")
    roles: List[Role] = Field(..., title="Roles")
    userEmail: Optional[str] = Field(None, title="UserEmail")
    activeDirectoryGroups: Optional[List[dict[str, str]]] = Field(None, title="ActiveDirectoryGroups")
    groupMemberships: List[Group] = Field([], title="GroupMemberships")

    @validator("roles", each_item=True, pre=True)
    def roles_upper_case(cls, v):
        return v.upper()
