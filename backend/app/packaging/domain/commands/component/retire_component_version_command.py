from typing import List

from pydantic import Field

from app.packaging.domain.value_objects.component import component_id_value_object
from app.packaging.domain.value_objects.component_version import component_version_id_value_object
from app.packaging.domain.value_objects.shared import user_id_value_object, user_role_value_object
from app.shared.adapters.message_bus import command_bus


class RetireComponentVersionCommand(command_bus.Command):
    componentId: component_id_value_object.ComponentIdValueObject
    componentVersionId: component_version_id_value_object.ComponentVersionIdValueObject
    userRoles: List[user_role_value_object.UserRoleValueObject] = Field(default_factory=list)
    serviceAuthorized: bool = False
    lastUpdatedBy: user_id_value_object.UserIdValueObject
