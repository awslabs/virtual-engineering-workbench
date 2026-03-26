import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import complete_provisioned_product_removal_command
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate


def handle(
    command: complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand,
    publisher: aggregate.AggregatePublisher,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    logger: logging.Logger,
):
    vt_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger, provisioned_product_entity=virtual_targets_qs.get_by_id(command.provisioned_product_id.value)
    )

    vt_provisioning.complete_removal(
        command=command,
    )

    publisher.publish(vt_provisioning)
