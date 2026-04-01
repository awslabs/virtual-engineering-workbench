from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionAmiShared(message_bus.Message):
    event_name: Literal["ProductVersionAmiShared"] = Field("ProductVersionAmiShared", alias="eventName")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    previous_event_name: str = Field(..., alias="previousEventName")
    old_version_id: Optional[str] = Field(None, alias="oldVersionId")
    model_config = ConfigDict(populate_by_name=True)
