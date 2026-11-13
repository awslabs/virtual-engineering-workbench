from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ImageImported(message_bus.Message):
    event_name: Literal["ImageImported"] = Field("ImageImported", alias="eventName")
    projectId: str = Field(..., title="projectId")
    imageId: str = Field(..., title="imageId")
    imageSource: str = Field(..., title="imageSource")
    amiId: str = Field(..., title="amiId")
    imageStatus: str = Field(..., title="imageStatus")
    imageName: Optional[str] = Field(None, title="imageName")
    imageDescription: Optional[str] = Field(None, title="imageDescription")
    platform: Optional[str] = Field(None, title="platform")
    architecture: Optional[str] = Field(None, title="architecture")
    osVersion: Optional[str] = Field(None, title="osVersion")
    componentVersionDetails: list[dict] = Field(default_factory=list, title="componentVersionDetails")
    marketplaceMetadata: Optional[dict] = Field(None, title="marketplaceMetadata")
    createDate: str = Field(..., title="createDate")
    model_config = ConfigDict(populate_by_name=True)
