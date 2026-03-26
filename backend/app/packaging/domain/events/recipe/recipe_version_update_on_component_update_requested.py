from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class RecipeVersionUpdateOnComponentUpdateRequested(message_bus.Message):
    event_name: str = Field("RecipeVersionUpdateOnComponentUpdateRequested", alias="eventName", const=True)
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    last_updated_by: str = Field(..., alias="lastUpdatedBy")

    class Config:
        allow_population_by_field_name = True
