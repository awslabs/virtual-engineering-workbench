import logging

from app.provisioning.domain.aggregates import provisioned_product_state_aggregate
from app.provisioning.domain.commands.provisioned_product_state import initiate_provisioned_product_start_command
from app.provisioning.domain.model import provisioned_product
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate


def handle(
    command: initiate_provisioned_product_start_command.InitiateProvisionedProductStartCommand,
    publisher: aggregate.AggregatePublisher,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    logger: logging.Logger,
):
    vt: provisioned_product.ProvisionedProduct | None = None

    vt = virtual_targets_qs.get_by_id(command.provisioned_product_id.value)

    vt_state = provisioned_product_state_aggregate.ProvisionedProductStateAggregate(
        logger=logger, provisioned_product=vt
    )

    vt_state.initiate_start_instance(command=command)

    publisher.publish(vt_state)
