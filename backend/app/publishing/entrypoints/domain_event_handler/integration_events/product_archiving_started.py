from pydantic import BaseModel, Field


class ProductArchivingStarted(BaseModel):
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
