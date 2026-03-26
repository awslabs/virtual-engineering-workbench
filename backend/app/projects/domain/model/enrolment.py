import enum
from typing import Optional
from uuid import uuid4

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class EnrolmentStatus(enum.StrEnum):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"


def uuid_to_str():
    unique_id = uuid4()
    return str(unique_id)


class EnrolmentPrimaryKey(unit_of_work.PrimaryKey):
    id: str = Field(..., title="Id")
    projectId: str = Field(..., title="ProjectId")


class Enrolment(unit_of_work.Entity):
    id: str = Field(default_factory=uuid_to_str, title="Id")
    projectId: str = Field(..., title="ProjectId")
    userId: str = Field(..., title="UserId")
    userEmail: Optional[str] = Field(None, title="UserEmail")
    status: EnrolmentStatus = Field(..., title="Status")
    ticketId: Optional[str] = Field(None, title="TicketId")
    ticketLink: Optional[str] = Field(None, title="TicketLink")
    approver: Optional[str] = Field(None, title="Approve")
    reason: Optional[str] = Field(None, title="Reason")
    createDate: Optional[str] = Field(None, title="CreateDate")
    lastUpdateDate: Optional[str] = Field(None, title="LastUpdateDate")
    resolveDate: Optional[str] = Field(None, title="ResolveDate")
    sourceSystem: Optional[str] = Field(None, title="SourceSystem")
