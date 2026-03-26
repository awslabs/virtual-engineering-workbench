import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import stop_provisioned_product_after_update_complete_command
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate


def handle(
    command: stop_provisioned_product_after_update_complete_command.StopProvisionedProductAfterUpdateCompleteCommand,
    publisher: aggregate.AggregatePublisher,
    provisioned_products_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    logger: logging.Logger,
):
    pp_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
        logger=logger,
        provisioned_product_entity=provisioned_products_qs.get_by_id(command.provisioned_product_id.value),
    )

    pp_provisioning.stop_after_update(command=command)

    publisher.publish(pp_provisioning)
