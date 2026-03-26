import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import authorize_user_ip_address_command
from app.provisioning.domain.ports import (
    instance_management_service,
    parameter_service,
    provisioned_products_query_service,
)


def handle(
    command: authorize_user_ip_address_command.AuthorizeUserIpAddressCommand,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    parameter_srv: parameter_service.ParameterService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    logger: logging.Logger,
    spoke_account_vpc_id_param_name: str,
    authorize_user_ip_address_param_value: bool,
):
    vt_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=virtual_targets_qs.get_by_id(command.provisioned_product_id.value),
    )

    vt_provisioning.authorize_user_ip_address(
        command=command,
        parameter_srv=parameter_srv,
        instance_mgmt_srv=instance_mgmt_srv,
        spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )
