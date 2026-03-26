from typing import Optional

from pydantic import BaseModel, Field


class ProductVersionPublished(BaseModel):
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    stage: str = Field(..., alias="stage")
    version_name: str = Field(..., alias="versionName")
    sc_product_id: str = Field(..., alias="scProductId")
    sc_provisioning_artifact_id: str = Field(..., alias="scProvisioningArtifactId")
    ami_id: Optional[str] = Field(None, alias="amiId")
