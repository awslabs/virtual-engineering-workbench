from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionUnpublished(message_bus.Message):
    event_name: Literal["ProductVersionUnpublished"] = Field("ProductVersionUnpublished", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    region: str = Field(..., alias="region")
    stage: str = Field(..., alias="stage")
    ami_id: str = Field(..., alias="amiId")
    has_integrations: bool = Field(False, alias="hasIntegrations")
    integrations: list[str] = Field([], alias="integrations")
    model_config = ConfigDict(populate_by_name=True)
