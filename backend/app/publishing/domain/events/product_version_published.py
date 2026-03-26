from typing import Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionPublished(message_bus.Message):
    event_name: str = Field("ProductVersionPublished", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    project_name: str = Field(..., alias="projectName")
    product_id: str = Field(..., alias="productId")
    product_name: str = Field(..., alias="productName")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    stage: str = Field(..., alias="stage")
    region: str = Field(..., alias="region")
    version_name: str = Field(..., alias="versionName")
    version_description: Optional[str] = Field(..., alias="versionDescription")
    sc_product_id: str = Field(..., alias="scProductId")
    sc_provisioning_artifact_id: str = Field(..., alias="scProvisioningArtifactId")
    ami_id: Optional[str] = Field(None, alias="amiId")
    platform: str | None = Field(None, alias="platform")
    architecture: str | None = Field(None, alias="architecture")
    has_integrations: bool = Field(False, alias="hasIntegrations")
    integrations: list[str] = Field([], alias="integrations")
    image_digest: Optional[str] = Field(None, alias="imageDigest")
    image_tag: Optional[str] = Field(None, alias="imageTag")

    class Config:
        allow_population_by_field_name = True
