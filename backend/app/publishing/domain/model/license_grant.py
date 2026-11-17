from enum import StrEnum

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class LicenseGrantStatus(StrEnum):
    PendingAcceptance = "PENDING_ACCEPTANCE"
    Active = "ACTIVE"
    Disabled = "DISABLED"
    Deleted = "DELETED"


class LicenseGrantPrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")
    grantId: str = Field(..., title="GrantId")


class LicenseGrant(unit_of_work.Entity):
    grantId: str = Field(..., title="GrantId")
    projectId: str = Field(..., title="ProjectId")
    imageId: str = Field(..., title="ImageId")
    licenseArn: str = Field(..., title="LicenseArn")
    grantArn: str = Field(..., title="GrantArn")
    homeRegion: str = Field(..., title="HomeRegion")
    targetAccountId: str = Field(..., title="TargetAccountId")
    status: LicenseGrantStatus = Field(..., title="Status")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
