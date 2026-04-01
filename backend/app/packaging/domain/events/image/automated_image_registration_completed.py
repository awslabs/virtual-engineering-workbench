from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.packaging.domain.model.component import component_version_detail
from app.shared.adapters.message_bus import message_bus


class AutomatedImageRegistrationCompleted(message_bus.Message):
    event_name: Literal["AutomatedImageRegistrationCompleted"] = Field(
        "AutomatedImageRegistrationCompleted", alias="eventName"
    )
    amiId: str = Field(..., title="amiId")
    productId: Optional[str] = Field(None, title="productId")
    projectId: str = Field(..., title="projectId")
    releaseType: str = Field(..., title="releaseType")
    userId: str = Field(..., title="userId")
    componentsVersionsDetails: list[component_version_detail.ComponentVersionDetail] = Field(
        ..., title="componentsVersionsDetails"
    )
    osVersion: str = Field(..., title="osVersion")
    platform: str = Field(..., title="platform")
    architecture: str = Field(..., title="architecture")
    integrations: list[str] = Field([], title="integrations")
    model_config = ConfigDict(populate_by_name=True)

    def model_dump_json(self, **kwargs) -> str:
        kwargs.setdefault("exclude_none", True)

        return super().model_dump_json(**kwargs)
