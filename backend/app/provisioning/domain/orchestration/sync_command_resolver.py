from __future__ import annotations

import typing

from app.provisioning.domain.commands.product_provisioning import (
    complete_product_launch_command,
    complete_provisioned_product_removal_command,
    complete_provisioned_product_update,
    fail_product_launch_command,
    fail_provisioned_product_removal_command,
    fail_provisioned_product_update,
)
from app.provisioning.domain.commands.provisioned_product_configuration import (
    fail_provisioned_product_configuration_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
)
from app.provisioning.domain.events.provisioned_product_sync import provisioned_product_status_out_of_sync
from app.provisioning.domain.model import product_status
from app.provisioning.domain.value_objects import failure_reason_value_object, provisioned_product_id_value_object
from app.shared.adapters.message_bus import command_bus

Predicate = typing.Callable[[provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync], bool]
CommandFactory = typing.Callable[[str], command_bus.Command]


class SyncCommandResolver:
    """
    A class that maps ProvisionedProductStatusOutOfSync event to commands based on a set of predicates and command factories.
    This class is used to resolve the command to be executed based on the event received.

    """

    def __init__(self) -> None:
        self._command_registry: list[dict[Predicate, CommandFactory]] = []

    def from_sync_event(
        self, event: provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync
    ) -> command_bus.Command | None:
        return next(
            (
                factory(event.provisioned_product_id)
                for (predicate, factory) in self._command_registry
                if predicate(event)
            ),
            None,
        )

    def map(self, predicate: Predicate, factory: CommandFactory) -> SyncCommandResolver:
        self._command_registry.append(
            {
                predicate: predicate,
                factory: factory,
            }
        )
        return self


def init():
    """
    This mapping defines how Provisioning BC resolves provisioned product synchronization problems.
    For example: if provisioned product has Deprovisioning status, but the product failed to deprovision,
    it will trigger FailProvisionedProductRemovalCommand.

    """

    return (
        SyncCommandResolver()
        .map(
            predicate=lambda event: event.new_status == product_status.ProductStatus.Terminated,
            factory=lambda provisioned_product_id: complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status
            in [product_status.ProductStatus.ProvisioningError, *product_status.ACTIVE_PRODUCT_STATUSES]
            and event.old_status
            in [product_status.ProductStatus.Deprovisioning, product_status.ProductStatus.Terminated],
            factory=lambda provisioned_product_id: fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status in product_status.ACTIVE_PRODUCT_STATUSES
            and event.old_status == product_status.ProductStatus.Provisioning,
            factory=lambda provisioned_product_id: complete_product_launch_command.CompleteProductLaunchCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status == product_status.ProductStatus.ProvisioningError
            and event.old_status == product_status.ProductStatus.Provisioning,
            factory=lambda provisioned_product_id: fail_product_launch_command.FailProductLaunchCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status in product_status.ACTIVE_PRODUCT_STATUSES
            and event.old_status == product_status.ProductStatus.Updating,
            factory=lambda provisioned_product_id: complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status == product_status.ProductStatus.ProvisioningError
            and event.old_status == product_status.ProductStatus.Updating,
            factory=lambda provisioned_product_id: fail_provisioned_product_update.FailProvisionedProductUpdateCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status == product_status.ProductStatus.Running,
            factory=lambda provisioned_product_id: complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status == product_status.ProductStatus.Stopped,
            factory=lambda provisioned_product_id: complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id)
            ),
        )
        .map(
            predicate=lambda event: event.new_status == product_status.ProductStatus.ConfigurationFailed,
            factory=lambda provisioned_product_id: fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand(
                provisioned_product_id=provisioned_product_id_value_object.from_str(provisioned_product_id),
                reason=failure_reason_value_object.from_str("Provisioned product is out of sync"),
            ),
        )
    )
