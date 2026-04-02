from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class UserProfileCleanedUp(message_bus.Message):
    event_name: Literal["UserProfileCleanedUp"] = Field("UserProfileCleanedUp", alias="eventName")
    user_id: str = Field(..., alias="userId")
