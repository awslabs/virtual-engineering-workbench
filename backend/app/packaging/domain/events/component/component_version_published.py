from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class ComponentVersionPublished(message_bus.Message):
    event_name: Literal["ComponentVersionPublished"] = Field("ComponentVersionPublished", alias="eventName")
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    model_config = ConfigDict(populate_by_name=True)
