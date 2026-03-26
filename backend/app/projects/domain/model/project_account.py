import enum
from uuid import uuid4

from pydantic import Field

from app.projects.domain.value_objects import account_type_value_object
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ProjectAccountStatusEnum(enum.StrEnum):
    Creating = "Creating"
    OnBoarding = "OnBoarding"
    Active = "Active"
    OffBoarding = "OffBoarding"
    ReOnboarding = "ReOnboarding"
    Archived = "Archived"
    Failed = "Failed"
    Inactive = "Inactive"


class ProjectAccountOnboardingResult(enum.StrEnum):
    Succeeded = "Succeeded"
    Failed = "Failed"


class ProjectAccountStageEnum(enum.StrEnum):
    DEV = "dev"
    QA = "qa"
    PROD = "prod"


def generate_id():
    return uuid_to_str


def uuid_to_str():
    unique_id = uuid4()
    return str(unique_id)


class ProjectAccountPrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")
    id: str = Field(..., title="Id")


class ProjectAccount(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    id: str = Field(default_factory=generate_id(), title="Id")
    awsAccountId: str = Field(..., title="AwsAccountId")
    accountType: account_type_value_object.AccountTypeEnum = Field(..., title="AccountType")
    accountName: str | None = Field(None, title="AccountName")
    accountDescription: str | None = Field(None, title="AccountDescription")
    createDate: str | None = Field(None, title="CreateDate")
    lastUpdateDate: str | None = Field(None, title="LastUpdateDate")
    accountStatus: ProjectAccountStatusEnum | None = Field(None, title="AccountStatus")
    technologyId: str | None = Field(None, title="TechnologyId")
    stage: ProjectAccountStageEnum = Field(..., title="Stage")
    region: str | None = Field(None, title="Region")
    lastOnboardingResult: ProjectAccountOnboardingResult | None = Field(None, title="LastOnboardingResult")
    lastOnboardingErrorMessage: str | None = Field(None, title="LastOnboardingErrorMessage")
    parameters: dict[str, str] | None = Field(None, title="Parameters")
