from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class UserProfileUpdated(message_bus.Message):
    event_name: str = Field("UserProfileUpdated", alias="eventName", const=True)
    user_id: str = Field(..., alias="userId")
