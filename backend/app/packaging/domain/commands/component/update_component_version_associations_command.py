from typing import Optional

from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import (
    component_version_id_value_object,
    components_versions_list_value_object,
)
from app.shared.adapters.message_bus import command_bus


class UpdateComponentVersionAssociationsCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionId: component_version_id_value_object.ComponentVersionIdValueObject
    componentsVersionDependencies: components_versions_list_value_object.ComponentsVersionsListValueObject
    previousComponentsVersionDependencies: Optional[
        components_versions_list_value_object.ComponentsVersionsListValueObject
    ]
