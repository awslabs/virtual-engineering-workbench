from typing import Optional

from pydantic import Field

from app.packaging.domain.model.component import component_version_detail
from app.shared.adapters.message_bus import message_bus


class AutomatedImageRegistrationCompleted(message_bus.Message):
    event_name: str = Field("AutomatedImageRegistrationCompleted", alias="eventName", const=True)
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

    class Config:
        allow_population_by_field_name = True

    def json(self, **kwargs) -> str:
        kwargs.setdefault("exclude_none", True)

        return super().json(**kwargs)
