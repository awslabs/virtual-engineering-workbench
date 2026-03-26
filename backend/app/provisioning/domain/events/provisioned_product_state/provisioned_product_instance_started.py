from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductInstanceStarted(message_bus.Message):
    event_name: str = Field("ProvisionedProductInstanceStarted", alias="eventName", const=True)
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
