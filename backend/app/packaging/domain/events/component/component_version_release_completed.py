from pydantic import Field

from app.packaging.domain.model.shared import component_version_entry
from app.shared.adapters.message_bus import message_bus


class ComponentVersionReleaseCompleted(message_bus.Message):
    event_name: str = Field("ComponentVersionReleaseCompleted", alias="eventName", const=True)
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    component_version_dependencies: list[component_version_entry.ComponentVersionEntry] = Field(
        list(), alias="componentVersionDependencies"
    )

    class Config:
        allow_population_by_field_name = True
