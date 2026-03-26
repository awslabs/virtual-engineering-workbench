from pydantic import BaseModel, Field


class ComponentVersionSummary(BaseModel):
    componentId: str = Field(..., title="ComponentId")
    componentVersionId: str = Field(..., title="ComponentVersionId")
    componentVersionName: str = Field(..., title="ComponentVersionName")
    componentName: str = Field(..., title="ComponentName")
