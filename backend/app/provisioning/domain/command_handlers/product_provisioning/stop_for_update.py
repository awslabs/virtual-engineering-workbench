import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import stop_provisioned_product_for_update_command
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    parameter_service,
    provisioned_products_query_service,
)
from app.shared.ddd import aggregate


def handle(
    command: stop_provisioned_product_for_update_command.StopProvisionedProductForUpdateCommand,
    publisher: aggregate.AggregatePublisher,
    provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    container_mgmt_srv: container_management_service.ContainerManagementService,
    logger: logging.Logger,
    parameter_srv: parameter_service.ParameterService,
    spoke_account_vpc_id_param_name: str,
    authorize_user_ip_address_param_value: bool,
):
    pp_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=provisioned_products_qs.get_by_id(command.provisioned_product_id.value),
    )

    pp_provisioning.stop_for_update(
        command=command,
        instance_mgmt_srv=instance_mgmt_srv,
        container_mgmt_srv=container_mgmt_srv,
        parameter_srv=parameter_srv,
        spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    publisher.publish(pp_provisioning)
