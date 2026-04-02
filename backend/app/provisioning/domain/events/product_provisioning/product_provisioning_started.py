from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductProvisioningStarted(message_bus.Message):
    event_name: Literal["ProductProvisioningStarted"] = Field("ProductProvisioningStarted", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    provisioned_compound_product_id: str | None = Field(None, alias="provisionedCompoundProductId")
