from __future__ import annotations

import typing

from app.provisioning.domain.commands.product_provisioning import update_provisioned_product_command
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
)
from app.provisioning.domain.model import product_status, provisioned_product
from app.provisioning.domain.value_objects import provisioned_product_id_value_object
from app.shared.adapters.message_bus import command_bus

Predicate = typing.Callable[[provisioned_product.ProvisionedProduct, product_status.EC2InstanceState], bool]
CommandFactory = typing.Callable[[str], command_bus.Command]


class EC2StateCommandResolver:
    """
    A class that maps new EC2 instance state to commands based on a set of predicates and command factories.
    This class is used to resolve the command to be executed based on the event received.

    """

    def __init__(self) -> None:
        self._command_registry: list[dict[Predicate, CommandFactory]] = []

    def from_ec2_state(
        self,
        provisioned_product: provisioned_product.ProvisionedProduct,
        ec2_state: product_status.EC2InstanceState,
    ) -> command_bus.Command | None:
        return next(
            (
                factory(provisioned_product.provisionedProductId)
                for (predicate, factory) in self._command_registry
                if predicate(provisioned_product, ec2_state)
            ),
            None,
        )

    def map(self, predicate: Predicate, factory: CommandFactory) -> EC2StateCommandResolver:
        self._command_registry.append(
            {
                predicate: predicate,
                factory: factory,
            }
        )
        return self


def init():
    """
    This mapping defines how Provisioning BC resolves EC2 state changes.
    For example: if provisioned product has Updating status, and the new EC2 state is Stopped,
    it will trigger UpdateProvisionedProductCommandHandler.

    """

    return (
        EC2StateCommandResolver()
        .map(
            predicate=lambda pp, new_state: pp.status == product_status.ProductStatus.Updating
            and new_state == product_status.EC2InstanceState.Stopped,
            factory=lambda provisioned_product_id: update_provisioned_product_command.UpdateProvisionedProductCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda pp, new_state: pp.status != product_status.ProductStatus.Updating
            and new_state == product_status.EC2InstanceState.Stopped,
            factory=lambda provisioned_product_id: complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda _, new_state: new_state == product_status.EC2InstanceState.Running,
            factory=lambda provisioned_product_id: complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
    )
