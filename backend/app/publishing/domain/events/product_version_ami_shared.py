from typing import Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionAmiShared(message_bus.Message):
    event_name: str = Field("ProductVersionAmiShared", alias="eventName", const=True)
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    previous_event_name: str = Field(..., alias="previousEventName")
    old_version_id: Optional[str] = Field(None, alias="oldVersionId")

    class Config:
        allow_population_by_field_name = True
