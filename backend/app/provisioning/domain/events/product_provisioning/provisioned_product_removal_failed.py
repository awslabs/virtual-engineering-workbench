from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProvisionedProductRemovalFailed(message_bus.Message):
    event_name: str = Field("ProvisionedProductRemovalFailed", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    provisioned_product_id: str = Field(..., alias="provisionedProductId")
    provisioned_compound_product_id: str | None = Field(None, alias="provisionedCompoundProductId")
