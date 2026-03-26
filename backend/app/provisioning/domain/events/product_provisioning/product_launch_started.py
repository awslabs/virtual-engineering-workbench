from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductLaunchStarted(message_bus.Message):
    event_name: str = Field("ProductLaunchStarted", alias="eventName", const=True)
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    user_ip_address: str = Field(..., alias="userIpAddress")
