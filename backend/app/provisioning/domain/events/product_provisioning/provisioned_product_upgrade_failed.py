from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductUpgradeFailed(message_bus.Message):
    event_name: str = Field("ProvisionedProductUpgradeFailed", alias="eventName", const=True)
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
