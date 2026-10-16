import enum

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ServiceClientAssignmentStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class ServiceClientAssignmentPrimaryKey(unit_of_work.PrimaryKey):
    clientId: str = Field(..., title="ClientId")
    projectId: str = Field(..., title="ProjectId")


class ServiceClientAssignment(unit_of_work.Entity):
    clientId: str = Field(..., title="ClientId")
    projectId: str = Field(..., title="ProjectId")
    status: ServiceClientAssignmentStatus = Field(..., title="Status")
    grantedBy: str = Field(..., title="GrantedBy")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
