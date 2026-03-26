import pydantic

from app.provisioning.domain.value_objects import (
    product_id_value_object,
    product_version_id_value_object,
    product_version_name_value_object,
    region_value_object,
    version_stage_value_object,
)
from app.shared.adapters.message_bus import command_bus


class CheckIfUpgradeAvailableCommand(command_bus.Command):
    product_id: product_id_value_object.ProductIdValueObject = pydantic.Field(...)
    product_version_id: product_version_id_value_object.ProductVersionIdValueObject = pydantic.Field(...)
    product_version_name: product_version_name_value_object.ProductVersionNameValueObject = pydantic.Field(...)
    region: region_value_object.RegionValueObject = pydantic.Field(...)
    stage: version_stage_value_object.VersionStageValueObject = pydantic.Field(...)
