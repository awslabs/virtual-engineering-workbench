from enum import StrEnum
from typing import Literal, Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class StartFailedReason(StrEnum):
    InsufficientInstanceCapacity = "INSUFFICIENT_INSTANCE_CAPACITY"
    InsufficientClusterCapacity = "INSUFFICIENT_CLUSTER_CAPACITY"


class ProvisionedProductStartFailed(message_bus.Message):
    event_name: Literal["ProvisionedProductStartFailed"] = Field("ProvisionedProductStartFailed", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    product_type: str = Field(..., alias="productType")
    product_name: str = Field(..., alias="productName")
    owner: str = Field(..., alias="owner")
    reason: Optional[StartFailedReason] = Field(None, alias="reason")
