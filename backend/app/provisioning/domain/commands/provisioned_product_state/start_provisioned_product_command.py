import pydantic

from app.provisioning.domain.value_objects import ip_address_value_object, provisioned_product_id_value_object
from app.shared.adapters.message_bus import command_bus


class StartProvisionedProductCommand(command_bus.Command):
    provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject = pydantic.Field(...)
    user_ip_address: ip_address_value_object.IpV4Address = pydantic.Field(...)
