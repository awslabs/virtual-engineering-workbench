from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ProductArchivingStarted(message_bus.Message):
    event_name: Literal["ProductArchivingStarted"] = Field("ProductArchivingStarted", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    model_config = ConfigDict(populate_by_name=True)
