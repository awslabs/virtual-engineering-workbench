import typing
from enum import Enum

from pydantic import BaseModel, Field


class ProjectAccountStatusEnum(str, Enum):
    Creating = "Creating"
    OnBoarding = "OnBoarding"
    Active = "Active"
    OffBoarding = "OffBoarding"
    ReOnboarding = "ReOnboarding"
    Archived = "Archived"
    Failed = "Failed"
    Inactive = "Inactive"

    def __str__(self):
        return str(self.value)


class ProjectAccount(BaseModel):
    id: str = Field(..., title="Id")
    awsAccountId: str = Field(..., title="AwsAccountId")
    stage: str = Field(..., title="Stage")
    region: typing.Optional[str] = Field(None, title="Region")
