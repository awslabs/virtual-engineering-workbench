from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionNameUpdated(message_bus.Message):
    event_name: Literal["ProductVersionNameUpdated"] = Field("ProductVersionNameUpdated", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    version_name: str = Field(..., alias="versionName")
    aws_account_id: str = Field(..., alias="awsAccountId")
    has_integrations: bool = Field(False, alias="hasIntegrations")
    integrations: list[str] = Field([], alias="integrations")
    model_config = ConfigDict(populate_by_name=True)
