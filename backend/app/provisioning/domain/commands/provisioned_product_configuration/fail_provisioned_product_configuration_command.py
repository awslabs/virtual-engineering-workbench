import pydantic

from app.provisioning.domain.value_objects import failure_reason_value_object, provisioned_product_id_value_object
from app.shared.adapters.message_bus import command_bus


class FailProvisionedProductConfigurationCommand(command_bus.Command):
    provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject = pydantic.Field(...)
    reason: failure_reason_value_object.FailureReason = pydantic.Field(...)
