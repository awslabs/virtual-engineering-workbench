from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductUpgradeAvailable(message_bus.Message):
    event_name: Literal["ProvisionedProductUpgradeAvailable"] = Field(
        "ProvisionedProductUpgradeAvailable", alias="eventName"
    )
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
