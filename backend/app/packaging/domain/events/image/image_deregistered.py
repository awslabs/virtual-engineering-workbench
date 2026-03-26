from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ImageDeregistered(message_bus.Message):
    event_name: str = Field("ImageDeregistered", alias="eventName", const=True)
    ami_id: str = Field(..., alias="amiId")
