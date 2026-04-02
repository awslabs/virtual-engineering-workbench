from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductStatusOutOfSync(message_bus.Message):
    event_name: Literal["ProvisionedProductStatusOutOfSync"] = Field(
        "ProvisionedProductStatusOutOfSync", alias="eventName"
    )
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    old_status: str = Field(..., alias="oldStatus")
    new_status: str = Field(..., alias="newStatus")
