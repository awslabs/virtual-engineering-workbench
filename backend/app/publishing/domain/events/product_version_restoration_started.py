from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionRestorationStarted(message_bus.Message):
    event_name: Literal["ProductVersionRestorationStarted"] = Field(
        "ProductVersionRestorationStarted", alias="eventName"
    )
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    old_version_id: str = Field(..., alias="oldVersionId")
    product_type: str = Field(..., alias="productType")
    model_config = ConfigDict(populate_by_name=True)
