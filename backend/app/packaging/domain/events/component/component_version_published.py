from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ComponentVersionPublished(message_bus.Message):
    event_name: str = Field("ComponentVersionPublished", alias="eventName", const=True)
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")

    class Config:
        allow_population_by_field_name = True
