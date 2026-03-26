import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import complete_provisioned_product_update
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    products_service,
    provisioned_products_query_service,
    versions_query_service,
)
from app.shared.ddd import aggregate


def handle(
    command: complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand,
    publisher: aggregate.AggregatePublisher,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    products_srv: products_service.ProductsService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    container_mgmt_srv: container_management_service.ContainerManagementService,
    logger: logging.Logger,
    versions_qs: versions_query_service.VersionsQueryService,
):
    pp_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger, provisioned_product_entity=virtual_targets_qs.get_by_id(command.provisioned_product_id.value)
    )

    pp_provisioning.complete_update(
        command=command,
        products_srv=products_srv,
        instance_mgmt_srv=instance_mgmt_srv,
        container_mgmt_srv=container_mgmt_srv,
        versions_qs=versions_qs,
    )

    publisher.publish(pp_provisioning)
