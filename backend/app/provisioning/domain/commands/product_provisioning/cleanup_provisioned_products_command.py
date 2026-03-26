from pydantic import Field

from app.provisioning.domain.value_objects import provisioned_product_cleanup_value_object
from app.shared.adapters.message_bus import command_bus


class CleanupProvisionedProductsCommand(command_bus.Command):
    provisioned_product_cleanup_config: (
        provisioned_product_cleanup_value_object.ProvisionedProductCleanupConfigValueObject
    ) = Field(...)
