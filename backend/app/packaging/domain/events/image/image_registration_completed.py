from pydantic import Field

from app.packaging.domain.model.component import component_version_detail
from app.shared.adapters.message_bus import message_bus


class ImageRegistrationCompleted(message_bus.Message):
    event_name: str = Field("ImageRegistrationCompleted", alias="eventName", const=True)
    projectId: str = Field(..., alias="projectId")
    amiDescription: str = Field(..., title="amiDescription")
    amiId: str = Field(..., title="amiId")
    amiName: str = Field(..., title="amiName")
    componentsVersionsDetails: list[component_version_detail.ComponentVersionDetail] = Field(
        ..., title="componentsVersionsDetails"
    )
    retiredAmiIds: list[str] = Field(..., title="retiredAmiIds")
    osVersion: str = Field(..., title="osVersion")
    platform: str = Field(..., title="platform")
    architecture: str = Field(..., title="architecture")
    integrations: list[str] = Field([], title="integrations")
    createDate: str = Field(..., title="createDate")

    class Config:
        allow_population_by_field_name = True
