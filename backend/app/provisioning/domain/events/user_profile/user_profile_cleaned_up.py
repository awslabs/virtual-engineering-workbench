from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class UserProfileCleanedUp(message_bus.Message):
    event_name: str = Field("UserProfileCleanedUp", alias="eventName", const=True)
    user_id: str = Field(..., alias="userId")
