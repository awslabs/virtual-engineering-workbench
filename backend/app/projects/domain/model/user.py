import enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class UserADStatus(enum.StrEnum):
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ActiveDirectoryGroup(BaseModel):
    domain: str = Field(..., title="Domain")
    groupName: str = Field(..., title="GroupName")
    model_config = ConfigDict(frozen=True)


class UserPrimaryKey(unit_of_work.PrimaryKey):
    userId: str = Field(..., title="UserId")


class User(unit_of_work.Entity):
    userId: str = Field(..., title="UserId")
    activeDirectoryGroups: list[ActiveDirectoryGroup] = Field(..., title="ActiveDirectoryGroups")
    activeDirectoryGroupStatus: UserADStatus = Field(UserADStatus.UNKNOWN, title="ActiveDirectoryGroupStatus")
    userEmail: Optional[str] = Field(None, title="UserEmail")
    model_config = ConfigDict(arbitrary_types_allowed=True)
