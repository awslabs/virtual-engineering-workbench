from pydantic import BaseModel, ConfigDict, Field


class RecommendedVersionSet(BaseModel):
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    model_config = ConfigDict(populate_by_name=True)
