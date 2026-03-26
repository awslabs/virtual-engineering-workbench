import logging

from app.provisioning.domain.aggregates import provisioned_product_state_aggregate
from app.provisioning.domain.commands.provisioned_product_state import stop_provisioned_product_command
from app.provisioning.domain.model import provisioned_product
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    provisioned_products_query_service,
)
from app.shared.ddd import aggregate


def handle(
    command: stop_provisioned_product_command.StopProvisionedProductCommand,
    publisher: aggregate.AggregatePublisher,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    instance_mgmt_srv: instance_management_service.InstanceManagementService,
    container_mgmt_srv: container_management_service.ContainerManagementService,
    logger: logging.Logger,
):
    vt: provisioned_product.ProvisionedProduct | None = None

    vt = virtual_targets_qs.get_by_id(command.provisioned_product_id.value)

    vt_state = provisioned_product_state_aggregate.ProvisionedProductStateAggregate(
        logger=logger, provisioned_product=vt
    )

    vt_state.stop_instance(command=command, instance_mgmt_srv=instance_mgmt_srv, container_mgmt_srv=container_mgmt_srv)

    publisher.publish(vt_state)
