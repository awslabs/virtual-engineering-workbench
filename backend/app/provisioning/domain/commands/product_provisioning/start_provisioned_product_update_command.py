import pydantic

from app.provisioning.domain.value_objects import (
    ip_address_value_object,
    is_auto_update_value_object,
    product_version_id_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    provisioning_parameters_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class StartProvisionedProductUpdateCommand(command_bus.Command):
    provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject = pydantic.Field(...)
    project_id: project_id_value_object.ProjectIdValueObject = pydantic.Field(...)
    user_id: user_id_value_object.UserIdValueObject = pydantic.Field(...)
    provisioning_parameters: provisioning_parameters_value_object.ProvisioningParametersValueObject = pydantic.Field(
        ...
    )
    user_ip_address: ip_address_value_object.IpV4Address | None = pydantic.Field(None)
    version_id: product_version_id_value_object.ProductVersionIdValueObject = pydantic.Field(...)
    is_auto_update: is_auto_update_value_object.IsAutoUpdateValueObject = pydantic.Field(...)
