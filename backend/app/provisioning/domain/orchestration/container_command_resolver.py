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

# Define type aliases for clarity
Predicate = typing.Callable[[provisioned_product.ProvisionedProduct, product_status.TaskState], bool]
CommandFactory = typing.Callable[[str], command_bus.Command]


class ContainerStateCommandResolver:
    """
    A class that maps new Container instance state to commands based on a set of predicates and command factories.
    This class is used to resolve the command to be executed based on the event received.
    """

    def __init__(self) -> None:
        self._command_registry: list[tuple[Predicate, CommandFactory]] = []

    def from_container_state(
        self,
        provisioned_product: provisioned_product.ProvisionedProduct,
        container_state: product_status.TaskState,
    ) -> command_bus.Command | None:
        return next(
            (
                factory(provisioned_product.provisionedProductId)
                for (predicate, factory) in self._command_registry
                if predicate(provisioned_product, container_state)
            ),
            None,
        )

    def map(self, predicate: Predicate, factory: CommandFactory) -> ContainerStateCommandResolver:
        self._command_registry.append((predicate, factory))
        return self

    def remove_mapping(self, predicate: Predicate) -> None:
        self._command_registry = [entry for entry in self._command_registry if entry[0] != predicate]


def update_command(provisioned_product_id: str) -> command_bus.Command:
    """
    Creates a command to update a provisioned product.

    :param provisioned_product_id: The ID of the provisioned product to update.
    :return: The command to update the provisioned product.
    """
    return update_provisioned_product_command.UpdateProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
    )


def complete_stop_command(provisioned_product_id: str) -> command_bus.Command:
    """
    Creates a command to stop a provisioned product.

    :param provisioned_product_id: The ID of the provisioned product to stop.
    :return: The command to stop the provisioned product.
    """
    return complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
    )


def complete_start_command(provisioned_product_id: str) -> command_bus.Command:
    """
    Creates a command to start a provisioned product.

    :param provisioned_product_id: The ID of the provisioned product to start.
    :return: The command to start the provisioned product.
    """
    return complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
    )


# Predicate functions
def is_updating_and_stopping(pp: provisioned_product.ProvisionedProduct, new_state: product_status.TaskState) -> bool:
    """
    Predicate to check if a provisioned product is updating and the new state is stopping or stopped.

    :param pp: The provisioned product being evaluated.
    :param new_state: The new container state.
    :return: True if the product is updating and the new state is stopping or stopped.
    """
    return pp.status == product_status.ProductStatus.Updating and new_state in [
        product_status.TaskState.Stopping,
        product_status.TaskState.Stopped,
    ]


def is_not_updating_and_stopping(
    pp: provisioned_product.ProvisionedProduct, new_state: product_status.TaskState
) -> bool:
    """
    Predicate to check if a provisioned product is not updating and the new state is stopping or stopped.

    :param pp: The provisioned product being evaluated.
    :param new_state: The new container state.
    :return: True if the product is not updating and the new state is stopping or stopped.
    """
    return pp.status != product_status.ProductStatus.Updating and new_state in [
        product_status.TaskState.Deprovisioning,
        product_status.TaskState.Stopping,
        product_status.TaskState.Stopped,
    ]


def is_running(pp: provisioned_product.ProvisionedProduct, new_state: product_status.TaskState) -> bool:
    """
    Predicate to check if the new container state is running.

    :param pp: The provisioned product (this parameter is not used in the predicate but must be present).
    :param new_state: The new container state.
    :return: True if the new state is Running.
    """
    return (
        pp.status in [product_status.ProductStatus.Provisioning, product_status.ProductStatus.Starting]
        and new_state == product_status.TaskState.Running
    )


def init() -> ContainerStateCommandResolver:
    """
    Initializes the mapping between container states and commands.

    This mapping defines how Provisioning BC resolves container state changes.
    For example: if the provisioned product has the Updating status, and the new container state is Inactive,
    it will trigger UpdateProvisionedProductCommandHandler.

    :return: The initialized ContainerStateCommandResolver instance.
    """
    return (
        ContainerStateCommandResolver()
        .map(
            predicate=is_updating_and_stopping,
            factory=update_command,
        )
        .map(
            predicate=is_not_updating_and_stopping,
            factory=complete_stop_command,
        )
        .map(
            predicate=is_running,
            factory=complete_start_command,
        )
    )
