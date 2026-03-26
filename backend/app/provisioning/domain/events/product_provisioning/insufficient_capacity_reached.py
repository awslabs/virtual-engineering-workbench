from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class InsufficientCapacityReached(message_bus.Message):
    event_name: str = Field("InsufficientCapacityReached", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    product_type: str = Field(..., alias="productType")
    product_name: str = Field(..., alias="productName")
    owner: str = Field(..., alias="owner")
    user_ip_address: str = Field(..., alias="userIpAddress")
