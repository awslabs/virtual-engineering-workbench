from pydantic import BaseModel, Field


class RecommendedVersionSet(BaseModel):
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")

    class Config:
        allow_population_by_field_name = True
