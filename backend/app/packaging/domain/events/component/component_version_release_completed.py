from typing import Literal

from pydantic import ConfigDict, Field

from app.packaging.domain.model.shared import component_version_entry
from app.shared.adapters.message_bus import message_bus


class ComponentVersionReleaseCompleted(message_bus.Message):
    event_name: Literal["ComponentVersionReleaseCompleted"] = Field(
        "ComponentVersionReleaseCompleted", alias="eventName"
    )
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    component_version_dependencies: list[component_version_entry.ComponentVersionEntry] = Field(
        list(), alias="componentVersionDependencies"
    )
    model_config = ConfigDict(populate_by_name=True)
