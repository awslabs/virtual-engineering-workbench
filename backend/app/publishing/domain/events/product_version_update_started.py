from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionUpdateStarted(message_bus.Message):
    event_name: str = Field("ProductVersionUpdateStarted", alias="eventName", const=True)
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    product_type: str = Field(..., alias="productType")

    class Config:
        allow_population_by_field_name = True
