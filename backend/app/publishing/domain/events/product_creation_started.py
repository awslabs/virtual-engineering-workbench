import typing

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductCreationStarted(message_bus.Message):
    event_name: str = Field("ProductCreationStarted", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    product_name: str = Field(..., alias="productName")
    product_description: typing.Optional[str] = Field(None, alias="productDescription")
    technology_id: str = Field(..., alias="technologyId")
    user_id: str = Field(..., alias="userId")
    product_id: str = Field(..., alias="productId")
    product_type: str = Field(..., alias="productType")

    class Config:
        allow_population_by_field_name = True
