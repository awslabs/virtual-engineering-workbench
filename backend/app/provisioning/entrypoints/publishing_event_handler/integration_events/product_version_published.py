from pydantic import BaseModel, ConfigDict, Field


class ProductVersionPublished(BaseModel):
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    version_name: str = Field(..., alias="versionName")
    stage: str = Field(..., alias="stage")
    region: str = Field(..., alias="region")
    model_config = ConfigDict(populate_by_name=True)
