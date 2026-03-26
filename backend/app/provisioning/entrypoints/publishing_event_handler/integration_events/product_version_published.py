from pydantic import BaseModel, Field


class ProductVersionPublished(BaseModel):
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    version_name: str = Field(..., alias="versionName")
    stage: str = Field(..., alias="stage")
    region: str = Field(..., alias="region")

    class Config:
        allow_population_by_field_name = True
