import logging

from app.provisioning.domain.aggregates import product_provisioning_aggregate
from app.provisioning.domain.commands.product_provisioning import (
    remove_provisioned_product_command,
    remove_provisioned_products_command,
)
from app.provisioning.domain.exceptions import domain_exception
from app.provisioning.domain.ports import provisioned_products_query_service
from app.shared.ddd import aggregate
from app.shared.middleware.authorization import VirtualWorkbenchRoles


def handle(
    command: remove_provisioned_products_command.RemoveProvisionedProductsCommand,
    publisher: aggregate.AggregatePublisher,
    logger: logging.Logger,
    virtual_targets_qs: provisioned_products_query_service.ProvisionedProductsQueryService,
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
        vt_provisioning = product_provisioning_aggregate.ProductProvisioningAggregate(
            logger=logger,
            provisioned_product_entity=virtual_targets_qs.get_by_id(provisioned_product_id.value),
        )

        remove_command = remove_provisioned_product_command.RemoveProvisionedProductCommand(
            provisioned_product_id=provisioned_product_id,
            project_id=command.project_id,
            user_id=command.user_id,
            user_roles=command.user_roles,
        )

        vt_provisioning.remove(
            command=remove_command,
        )

        publisher.publish(vt_provisioning)
