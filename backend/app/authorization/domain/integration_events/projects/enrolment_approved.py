import typing

from pydantic import BaseModel, Field

from app.authorization.domain.read_models import project_assignment


class EnrolmentApproved(BaseModel):
    program_id: str = Field(..., alias="programId")
    program_name: str = Field(..., alias="programName")
    user_id: str = Field(..., alias="userId")
    user_email: typing.Optional[str] = Field(
        ..., alias="userEmail"
    )  # Required but nullable: callers must explicitly pass this field, even if the value is None
    enrolment_id: str = Field(..., alias="enrolmentId")
    roles: list[project_assignment.Role] = Field([], alias="roles")
    groupMemberships: list[project_assignment.Group] = Field([], alias="groupMemberships")
