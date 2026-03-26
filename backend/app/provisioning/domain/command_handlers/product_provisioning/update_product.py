import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.aggregates.internal import networking_helpers
from app.provisioning.domain.commands.product_provisioning import update_provisioned_product_command
from app.provisioning.domain.model import user_profile
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    parameter_service,
    products_service,
    provisioned_products_query_service,
    versions_query_service,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate


def handle(
    command: update_provisioned_product_command.UpdateProvisionedProductCommand,
    publisher: aggregate.AggregatePublisher,
    products_srv: products_service.ProductsService,
    provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    container_mgmt_srv: container_management_service.ContainerManagementService,
    logger: logging.Logger,
    versions_qs: versions_query_service.VersionsQueryService,
    parameter_srv: parameter_service.ParameterService,
    spoke_account_vpc_id_param_name: str,
    subnet_selector: networking_helpers.SubnetSelector,
    uow: unit_of_work.UnitOfWork,
):
    provisioned_product = provisioned_products_qs.get_by_id(command.provisioned_product_id.value)

    with uow:
        user_profile_entity = uow.get_repository(user_profile.UserProfilePrimaryKey, user_profile.UserProfile).get(
            pk=user_profile.UserProfilePrimaryKey(
                userId=provisioned_product.userId,
            ),
        )

    pp_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=provisioned_product,
        user_profile_entity=user_profile_entity,
    )

    pp_provisioning.update_product(
        command=command,
        products_srv=products_srv,
        instance_mgmt_srv=instance_mgmt_srv,
        container_mgmt_srv=container_mgmt_srv,
        versions_qs=versions_qs,
        parameter_srv=parameter_srv,
        subnet_selector=subnet_selector,
        spoke_account_vpc_id_param_name=spoke_account_vpc_id_param_name,
    )

    publisher.publish(pp_provisioning)
