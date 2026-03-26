from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductStatusOutOfSync(message_bus.Message):
    event_name: str = Field("ProvisionedProductStatusOutOfSync", alias="eventName", const=True)
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    old_status: str = Field(..., alias="oldStatus")
    new_status: str = Field(..., alias="newStatus")
