from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class RecommendedVersionSet(message_bus.Message):
    event_name: str = Field("RecommendedVersionSet", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    version_id: str = Field(..., alias="versionId")

    class Config:
        allow_population_by_field_name = True
