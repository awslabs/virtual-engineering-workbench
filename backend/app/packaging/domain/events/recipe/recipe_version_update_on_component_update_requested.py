from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class RecipeVersionUpdateOnComponentUpdateRequested(message_bus.Message):
    event_name: Literal["RecipeVersionUpdateOnComponentUpdateRequested"] = Field(
        "RecipeVersionUpdateOnComponentUpdateRequested", alias="eventName"
    )
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    last_updated_by: str = Field(..., alias="lastUpdatedBy")
    model_config = ConfigDict(populate_by_name=True)
