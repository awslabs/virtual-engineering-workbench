from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class LicenseGrantCreated(message_bus.Message):
    event_name: Literal["LicenseGrantCreated"] = Field("LicenseGrantCreated", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    image_id: str = Field(..., alias="imageId")
    grant_id: str = Field(..., alias="grantId")
    grant_arn: str = Field(..., alias="grantArn")
    target_account_id: str = Field(..., alias="targetAccountId")
    license_arn: str = Field(..., alias="licenseArn")
    model_config = ConfigDict(populate_by_name=True)
