import enum
from typing import Optional

from pydantic import BaseModel, Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class UserADStatus(enum.StrEnum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ActiveDirectoryGroup(BaseModel):
    domain: str = Field(..., field="Domain")
    groupName: str = Field(..., field="GroupName")

    class Config:
        frozen = True


class UserPrimaryKey(unit_of_work.PrimaryKey):
    userId: str = Field(..., title="UserId")


class User(unit_of_work.Entity):
    userId: str = Field(..., title="UserId")
    activeDirectoryGroups: list[ActiveDirectoryGroup] = Field(..., title="ActiveDirectoryGroups")
    activeDirectoryGroupStatus: UserADStatus = Field(UserADStatus.UNKNOWN, title="ActiveDirectoryGroupStatus")
    userEmail: Optional[str] = Field(None, title="UserEmail")

    class Config:
        arbitrary_types_allowed = True
