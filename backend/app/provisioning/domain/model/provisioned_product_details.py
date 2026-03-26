from pydantic import BaseModel, Field


class ProvisionedProductTag(BaseModel):
    key: str = Field(..., alias="Key")
    value: str = Field(..., alias="Value")


class ProvisionedProductDetails(BaseModel):
    tags: list[ProvisionedProductTag] = Field(..., alias="Tags")
    status: str = Field(..., alias="Status")
    id: str = Field(..., alias="Id")
    provisioning_artifact_id: str = Field(..., alias="ProvisioningArtifactId")
