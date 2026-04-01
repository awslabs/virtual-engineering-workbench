from typing import Literal, Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProjectAccountOnBoardingStarted(message_bus.Message):
    event_name: Literal["accountonboarding-request"] = Field("accountonboarding-request", alias="eventName")
    program_account_id: str = Field(..., alias="programAccountId")
    account_id: str = Field(..., alias="accountId")
    account_type: str = Field(..., alias="accountType")
    account_program_name: str = Field(..., alias="programName")
    account_program_id: str = Field(..., alias="programId")
    account_environment: str = Field(..., alias="accountEnvironment")
    region: str = Field(..., alias="region")
    variables: Optional[dict[str, str]] = Field(None, alias="variables")
