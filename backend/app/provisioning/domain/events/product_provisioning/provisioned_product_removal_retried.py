from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductRemovalRetried(message_bus.Message):
    event_name: Literal["ProvisionedProductRemovalRetried"] = Field(
        "ProvisionedProductRemovalRetried", alias="eventName"
    )
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
