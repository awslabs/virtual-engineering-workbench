from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductDormantCleanupFailed(message_bus.Message):
    event_name: Literal["ProvisionedProductDormantCleanupFailed"] = Field(
        "ProvisionedProductDormantCleanupFailed", alias="eventName"
    )
