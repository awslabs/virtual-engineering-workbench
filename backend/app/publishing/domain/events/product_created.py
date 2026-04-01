import typing
from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ProductCreated(message_bus.Message):
    event_name: Literal["ProductCreated"] = Field("ProductCreated", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    product_name: str = Field(..., alias="productName")
    product_description: typing.Optional[str] = Field(None, alias="productDescription")
    technology_id: str = Field(..., alias="technologyId")
    user_id: str = Field(..., alias="userId")
    product_id: str = Field(..., alias="productId")
    product_type: str = Field(..., alias="productType")
    model_config = ConfigDict(populate_by_name=True)
