import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import cleanup_provisioned_products_command
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate


def handle(
    command: cleanup_provisioned_products_command.CleanupProvisionedProductsCommand,
    provisioned_products_qry_srv: provisioned_products_query_service.ProvisionedProductsQueryService,
    logger: logging.Logger,
    publisher: aggregate.AggregatePublisher,
):

    for provisioned_product in provisioned_products_qry_srv.get_all_provisioned_products(
        exclude_terminated=True, exclude_running=True
    ):
        prov_aggregate = product_provisioning_aggregate.ProductProvisioningAggregate(
            logger=logger,
            provisioned_product_entity=provisioned_product,
        )

        prov_aggregate.cleanup_provisioned_product(command)

        publisher.publish(prov_aggregate)

    return True
