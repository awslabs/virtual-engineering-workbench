from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductStopForUpgradeFailed(message_bus.Message):
    event_name: str = Field("ProvisionedProductStopForUpgradeFailed", alias="eventName", const=True)
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
