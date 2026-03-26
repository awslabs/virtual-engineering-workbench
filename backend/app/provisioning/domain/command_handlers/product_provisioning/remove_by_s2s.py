import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import remove_provisioned_product_command
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate


def handle(
    command: remove_provisioned_product_command.RemoveProvisionedProductCommand,
    publisher: aggregate.AggregatePublisher,
    logger: logging.Logger,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
):
    vt_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=virtual_targets_qs.get_by_id(command.provisioned_product_id.value),
    )

    vt_provisioning.remove(
        command=command,
        s2s_initiated=True,
    )

    publisher.publish(vt_provisioning)
