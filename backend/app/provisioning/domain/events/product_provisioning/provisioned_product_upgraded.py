from typing import Literal, Optional

from pydantic import AliasChoices, Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductUpgraded(message_bus.Message):
    event_name: Literal["ProvisionedProductUpgraded"] = Field("ProvisionedProductUpgraded", alias="eventName")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    aws_account_id: str = Field(None, alias="awsAccountId")
    region: str = Field(
        ...,
        validation_alias=AliasChoices("region", "Region"),
        serialization_alias="region",
    )
    old_instance_id: Optional[str] = Field(None, alias="oldInstanceId")
    instance_id: Optional[str] = Field(None, alias="instanceId")
    project_id: str = Field(..., alias="projectId")
    owner: str = Field(..., alias="owner")
    private_ip: str | None = Field(None, alias="privateIp")
    product_type: str = Field(..., alias="productType")
    product_name: str = Field(..., alias="productName")
