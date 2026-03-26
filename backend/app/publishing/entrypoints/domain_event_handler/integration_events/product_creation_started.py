import typing

from pydantic import BaseModel, Field


class ProductCreationStarted(BaseModel):
    project_id: str = Field(..., alias="projectId")
    product_name: str = Field(..., alias="productName")
    product_description: typing.Optional[str] = Field(None, alias="productDescription")
    technology_id: str = Field(..., alias="technologyId")
    user_id: str = Field(..., alias="userId")
    product_id: str = Field(..., alias="productId")
    product_type: str = Field(..., alias="productType")
