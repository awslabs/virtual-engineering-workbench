from typing import Optional

from pydantic import BaseModel, Field

from app.provisioning.domain.read_models import product


class ProductAvailabilityUpdated(BaseModel):
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    technology_id: str = Field(..., alias="technologyId")
    technology_name: str = Field(..., alias="technologyName")
    product_name: str = Field(..., alias="productName")
    product_type: product.ProductType = Field(..., alias="productType")
    product_description: Optional[str] = Field(None, alias="productDescription")
    available_stages: Optional[list[product.ProductStage]] = Field(None, alias="availableStages")
    available_regions: Optional[list[str]] = Field(None, alias="availableRegions")
    paused_stages: Optional[list[product.ProductStage]] = Field(None, alias="pausedStages")
    paused_regions: Optional[list[str]] = Field(None, alias="pausedRegions")
    last_update_date: str = Field(..., alias="lastUpdateDate")
