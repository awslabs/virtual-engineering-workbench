import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.commands.product_provisioning import provision_product_command
from app.provisioning.domain.model import user_profile
from app.provisioning.domain.ports import (
    instance_management_service,
    parameter_service,
    products_service,
    provisioned_products_query_service,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate


def handle(
    command: provision_product_command.ProvisionProductCommand,
    publisher: aggregate.AggregatePublisher,
    products_srv: products_service.ProductsService,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    parameter_srv: parameter_service.ParameterService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    logger: logging.Logger,
    spoke_account_vpc_id_param_name: str,
    subnet_selector: networking_helpers.SubnetSelector,
    authorize_user_ip_address_param_value: bool,
    uow: unit_of_work.UnitOfWork,
):
    provisioned_product = virtual_targets_qs.get_by_id(command.provisioned_product_id.value)

    with uow:
        user_profile_entity = uow.get_repository(user_profile.UserProfilePrimaryKey, user_profile.UserProfile).get(
            pk=user_profile.UserProfilePrimaryKey(
                userId=provisioned_product.userId,
            ),
        )

    vt_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=provisioned_product,
        user_profile_entity=user_profile_entity,
    )

    vt_provisioning.provision_product(
        command=command,
        products_srv=products_srv,
        parameter_srv=parameter_srv,
        instance_mgmt_srv=instance_mgmt_srv,
        spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
        subnet_selector=subnet_selector,
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    publisher.publish(vt_provisioning)
