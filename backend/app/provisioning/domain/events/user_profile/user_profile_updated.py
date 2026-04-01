from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class UserProfileUpdated(message_bus.Message):
    event_name: Literal["UserProfileUpdated"] = Field("UserProfileUpdated", alias="eventName")
    user_id: str = Field(..., alias="userId")
