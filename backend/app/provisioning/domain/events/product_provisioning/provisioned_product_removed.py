from typing import Literal, Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductRemoved(message_bus.Message):
    event_name: Literal["ProvisionedProductRemoved"] = Field("ProvisionedProductRemoved", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    provisioned_compound_product_id: str | None = Field(None, alias="provisionedCompoundProductId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    region: str = Field(..., alias="region")
    instance_id: Optional[str] = Field(None, alias="instanceId")
