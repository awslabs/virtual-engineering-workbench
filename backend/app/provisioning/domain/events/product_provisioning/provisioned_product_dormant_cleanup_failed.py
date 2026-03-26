from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductDormantCleanupFailed(message_bus.Message):
    event_name: str = Field("ProvisionedProductDormantCleanupFailed", alias="eventName", const=True)
