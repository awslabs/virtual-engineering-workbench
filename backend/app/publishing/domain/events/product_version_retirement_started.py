from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProductVersionRetirementStarted(message_bus.Message):
    event_name: str = Field("ProductVersionRetirementStarted", alias="eventName", const=True)
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")
    aws_account_id: str = Field(..., alias="awsAccountId")

    class Config:
        allow_population_by_field_name = True
