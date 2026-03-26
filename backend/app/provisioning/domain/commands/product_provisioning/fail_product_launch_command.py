import pydantic

from app.provisioning.domain.value_objects import provisioned_product_id_value_object
from app.shared.adapters.message_bus import command_bus


class FailProductLaunchCommand(command_bus.Command):
    provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject = pydantic.Field(...)
