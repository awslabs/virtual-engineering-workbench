from typing import Literal, Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductLaunched(message_bus.Message):
    event_name: Literal["ProductLaunched"] = Field("ProductLaunched", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    provisioned_compound_product_id: str | None = Field(None, alias="provisionedCompoundProductId")
    product_type: str = Field(..., alias="productType")
    product_name: str = Field(..., alias="productName")
    owner: str = Field(..., alias="owner")
    instance_id: Optional[str] = Field(None, alias="instanceId")
    private_ip: str = Field(..., alias="privateIP")
    service_id: Optional[str] = Field(None, alias="serviceId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    region: str = Field(..., alias="region")
    container_task_arn: Optional[str] = Field(None, alias="containerTaskArn")
