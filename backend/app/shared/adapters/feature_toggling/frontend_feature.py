from pydantic import BaseModel, Field


class FrontendFeature(BaseModel):
    version: str = Field(..., title="Version")
    feature: str = Field(..., title="Feature")
    enabled: bool = Field(..., title="Enabled")
