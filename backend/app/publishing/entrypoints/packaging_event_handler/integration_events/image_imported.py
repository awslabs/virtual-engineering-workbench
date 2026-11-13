from typing import Literal, Optional

from pydantic import BaseModel, Field


class ImageImported(BaseModel):
    event_name: Literal["ImageImported"] = Field("ImageImported", alias="eventName")
    projectId: str = Field(..., title="projectId")
    imageId: str = Field(..., title="imageId")
    amiId: str = Field(..., title="amiId")
    imageSource: str = Field(..., title="imageSource")
    imageStatus: str = Field(..., title="imageStatus")
    imageName: str = Field(..., title="imageName")
    imageDescription: Optional[str] = Field(None, title="imageDescription")
    platform: Optional[str] = Field(None, title="platform")
    architecture: Optional[str] = Field(None, title="architecture")
    osVersion: Optional[str] = Field(None, title="osVersion")
    componentVersionDetails: list[dict] = Field(default_factory=list, title="componentVersionDetails")
    marketplaceMetadata: Optional[dict] = Field(None, title="marketplaceMetadata")
    createDate: str = Field(..., title="createDate")
