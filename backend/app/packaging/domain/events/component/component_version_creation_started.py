from pydantic import Field

from app.packaging.domain.model.shared import component_version_entry
from app.shared.adapters.message_bus import message_bus


class ComponentVersionCreationStarted(message_bus.Message):
    event_name: str = Field("ComponentVersionCreationStarted", alias="eventName", const=True)
    component_id: str = Field(..., alias="componentId")
    component_version_id: str = Field(..., alias="componentVersionId")
    component_version_description: str = Field(..., alias="componentVersionDescription")
    component_version_name: str = Field(..., alias="componentVersionName")
    component_version_yaml_definition: str = Field(..., alias="componentVersionYamlDefinition")
    component_version_dependencies: list[component_version_entry.ComponentVersionEntry] = Field(
        list(), alias="componentVersionDependencies"
    )

    class Config:
        allow_population_by_field_name = True
