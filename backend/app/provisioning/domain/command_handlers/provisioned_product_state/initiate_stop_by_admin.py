import logging

from app.provisioning.domain.aggregates import provisioned_product_state_aggregate
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_stop_command,
    initiate_provisioned_products_stop_command,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.model import provisioned_product
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def handle(
    command: initiate_provisioned_products_stop_command.InitiateProvisionedProductsStopCommand,
    publisher: aggregate.AggregatePublisher,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
    logger: logging.Logger,
):
    if not (
        any(
            [
                item.value in [VirtualWorkbenchRoles.Admin, VirtualWorkbenchRoles.ProgramOwner]
                for item in (command.user_roles or [])
            ]
        )
    ):
        raise domain_exception.DomainException("User is not allowed to modify the requested provisioned products.")

    for provisioned_product_id in command.provisioned_product_ids:
        vt: provisioned_product.ProvisionedProduct | None = None

        vt = virtual_targets_qs.get_by_id(provisioned_product_id.value)

        vt_state = provisioned_product_state_aggregate.ProvisionedProductStateAggregate(
            logger=logger, provisioned_product=vt
        )

        intiate_stop_command = initiate_provisioned_product_stop_command.InitiateProvisionedProductStopCommand(
            provisioned_product_id=provisioned_product_id,
            project_id=command.project_id,
            user_id=command.user_id,
            user_roles=command.user_roles,
        )

        vt_state.initiate_stop_instance(command=intiate_stop_command)

        publisher.publish(vt_state)
