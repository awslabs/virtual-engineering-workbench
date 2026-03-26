from app.packaging.domain.value_objects.component import (
    component_build_version_arn_value_object,
    component_id_value_object,
)
from app.packaging.domain.value_objects.component_version import component_version_id_value_object
from app.shared.adapters.message_bus import command_bus


class RemoveComponentVersionCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionId: component_version_id_value_object.ComponentVersionIdValueObject
    componentBuildVersionArn: component_build_version_arn_value_object.ComponentBuildVersionArnValueObject
