from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductArchivingStarted(message_bus.Message):
    event_name: str = Field("ProductArchivingStarted", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")

    class Config:
        allow_population_by_field_name = True
