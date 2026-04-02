from typing import Literal

from pydantic import BaseModel, Field


class ImageDeregistered(BaseModel):
    event_name: Literal["ImageDeregistered"] = Field("ImageDeregistered", alias="eventName")
    ami_id: str = Field(..., alias="amiId")
