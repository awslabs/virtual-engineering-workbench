from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductConfigurationRequested(message_bus.Message):
    event_name: str = Field("ProvisionedProductConfigurationRequested", alias="eventName", const=True)
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
