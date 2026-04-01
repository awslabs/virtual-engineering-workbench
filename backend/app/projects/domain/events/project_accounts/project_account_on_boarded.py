from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProjectAccountOnBoarded(message_bus.Message):
    event_name: Literal["ProjectAccountOnBoarded"] = Field("ProjectAccountOnBoarded", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    technology_id: str = Field(..., alias="technologyId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    account_id: str = Field(..., alias="accountId")
    account_type: str = Field(..., alias="accountType")
    stage: str = Field(..., alias="stage")
    region: str = Field(..., alias="region")
