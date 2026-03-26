import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import fail_provisioned_product_update
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    products_service,
    provisioned_products_query_service,
)
from app.shared.ddd import aggregate


def handle(
    command: fail_provisioned_product_update.FailProvisionedProductUpdateCommand,
    publisher: aggregate.AggregatePublisher,
    provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    logger: logging.Logger,
    products_srv: products_service.ProductsService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    container_mgmt_srv: container_management_service.ContainerManagementService,
):
    pp_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=provisioned_products_qs.get_by_id(command.provisioned_product_id.value),
    )

    pp_provisioning.fail_update(
        command=command,
        products_srv=products_srv,
        instance_mgmt_srv=instance_mgmt_srv,
        container_mgmt_srv=container_mgmt_srv,
    )

    publisher.publish(pp_provisioning)
