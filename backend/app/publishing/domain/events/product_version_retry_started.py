from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionRetryStarted(message_bus.Message):
    event_name: Literal["ProductVersionRetryStarted"] = Field("ProductVersionRetryStarted", alias="eventName")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    product_type: str = Field(..., alias="productType")
    model_config = ConfigDict(populate_by_name=True)
