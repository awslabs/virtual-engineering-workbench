from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ImageDeregistered(message_bus.Message):
    event_name: Literal["ImageDeregistered"] = Field("ImageDeregistered", alias="eventName")
    ami_id: str = Field(..., alias="amiId")
