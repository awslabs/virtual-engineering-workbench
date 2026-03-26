import pydantic

from app.provisioning.domain.value_objects import (
    additional_configurations_value_object,
    deployment_option_value_object,
    ip_address_value_object,
    product_id_value_object,
    product_version_id_value_object,
    project_id_value_object,
    provisioned_compound_product_id_value_object,
    provisioned_product_id_value_object,
    provisioned_product_stage_value_object,
    provisioning_parameters_value_object,
    region_value_object,
    user_domains_value_object,
    user_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class LaunchProductCommand(command_bus.Command):
    provisioned_product_id: provisioned_product_id_value_object.ProvisionedProductIdValueObject = pydantic.Field(...)
    project_id: project_id_value_object.ProjectIdValueObject = pydantic.Field(...)
    user_id: user_id_value_object.UserIdValueObject = pydantic.Field(...)
    product_id: product_id_value_object.ProductIdValueObject = pydantic.Field(...)
    version_id: product_version_id_value_object.ProductVersionIdValueObject = pydantic.Field(...)
    provisioning_parameters: provisioning_parameters_value_object.ProvisioningParametersValueObject = pydantic.Field(
        ...
    )
    additional_configurations: additional_configurations_value_object.AdditionalConfigurationsValueObject = (
        pydantic.Field(...)
    )
    stage: provisioned_product_stage_value_object.ProvisionedProductStageValueObject = pydantic.Field(...)
    region: region_value_object.RegionValueObject = pydantic.Field(...)
    user_domains: user_domains_value_object.UserDomainsValueObject = pydantic.Field(...)
    user_ip_address: ip_address_value_object.IpV4Address = pydantic.Field(...)
    provisioned_compound_product_id: (
        provisioned_compound_product_id_value_object.ProvisionedCompoundProductIdValueObject
    ) = pydantic.Field(provisioned_compound_product_id_value_object.no_id())
    deployment_option: deployment_option_value_object.DeploymentOptionValueObject = pydantic.Field(...)
