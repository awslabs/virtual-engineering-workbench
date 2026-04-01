from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductConfigurationRequested(message_bus.Message):
    event_name: Literal["ProvisionedProductConfigurationRequested"] = Field(
        "ProvisionedProductConfigurationRequested", alias="eventName"
    )
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
