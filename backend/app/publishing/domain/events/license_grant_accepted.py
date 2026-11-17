from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class LicenseGrantAccepted(message_bus.Message):
    event_name: Literal["LicenseGrantAccepted"] = Field("LicenseGrantAccepted", alias="eventName")
    grant_id: str = Field(..., alias="grantId")
    grant_arn: str = Field(..., alias="grantArn")
    target_account_id: str = Field(..., alias="targetAccountId")
    model_config = ConfigDict(populate_by_name=True)
