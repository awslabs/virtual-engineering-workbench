import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import start_provisioned_product_update_command
from app.provisioning.domain.ports import provisioned_products_query_service, versions_query_service
from app.shared.ddd import aggregate


def handle(
    command: start_provisioned_product_update_command.StartProvisionedProductUpdateCommand,
    publisher: aggregate.AggregatePublisher,
    logger: logging.Logger,
    provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    versions_qs: versions_query_service.VersionsQueryService,
):
    pp_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=provisioned_products_qs.get_by_id(command.provisioned_product_id.value),
    )

    pp_provisioning.start_update(command=command, versions_qs=versions_qs)

    publisher.publish(pp_provisioning)
