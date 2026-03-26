import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import deprovision_provisioned_product_command
from app.provisioning.domain.ports import products_service, provisioned_products_query_service
from app.shared.ddd import aggregate


def handle(
    command: deprovision_provisioned_product_command.DeprovisionProvisionedProductCommand,
    publisher: aggregate.AggregatePublisher,
    products_srv: products_service.ProductsService,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    logger: logging.Logger,
):
    vt_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=virtual_targets_qs.get_by_id(command.provisioned_product_id.value),
    )

    vt_provisioning.deprovision_product(command=command, products_srv=products_srv)

    publisher.publish(vt_provisioning)
