from typing import Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductUpgraded(message_bus.Message):
    event_name: str = Field("ProvisionedProductUpgraded", alias="eventName", const=True)
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    aws_account_id: str = Field(None, alias="awsAccountId")
    region: str = Field(None, alias="Region")
    old_instance_id: Optional[str] = Field(None, alias="oldInstanceId")
    instance_id: Optional[str] = Field(None, alias="instanceId")
    project_id: str = Field(..., alias="projectId")
    owner: str = Field(..., alias="owner")
    private_ip: str | None = Field(None, alias="privateIp")
    product_type: str = Field(..., alias="productType")
    product_name: str = Field(..., alias="productName")
