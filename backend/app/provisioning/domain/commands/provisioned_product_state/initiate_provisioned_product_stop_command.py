from typing import Optional

import pydantic

from app.provisioning.domain.value_objects import (
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
    user_role_value_object,
)
from app.shared.adapters.message_bus import command_bus


class InitiateProvisionedProductStopCommand(command_bus.Command):
    provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject = pydantic.Field(...)
    project_id: project_id_value_object.ProjectIdValueObject = pydantic.Field(...)
    user_id: user_id_value_object.UserIdValueObject = pydantic.Field(...)
    user_roles: Optional[list[user_role_value_object.UserRoleValueObject]] = pydantic.Field(None)
