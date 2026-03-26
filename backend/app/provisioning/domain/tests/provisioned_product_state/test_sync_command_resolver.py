import assertpy
import pytest

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
from app.provisioning.domain.model.product_status import ProductStatus
from app.provisioning.domain.orchestration import sync_command_resolver


@pytest.fixture
def out_of_sync_event():
    def _out_of_sync_event(new_status: ProductStatus, old_status: ProductStatus):
        return provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync(
            provisionedProductId="pp-123",
            newStatus=new_status,
            oldStatus=old_status,
        )

    return _out_of_sync_event


@pytest.fixture
def sync_cmd_resolver():
    return sync_command_resolver.init()


@pytest.mark.parametrize(
    "new_status,old_status,expected_command",
    [
        (
            ProductStatus.Terminated,
            ProductStatus.Deprovisioning,
            complete_provisioned_product_removal_command.CompleteProvisionedProductRemovalCommand,
        ),
        (
            ProductStatus.ProvisioningError,
            ProductStatus.Deprovisioning,
            fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
        ),
        (
            ProductStatus.Running,
            ProductStatus.Deprovisioning,
            fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
        ),
        (
            ProductStatus.Stopped,
            ProductStatus.Deprovisioning,
            fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
        ),
        (
            ProductStatus.ProvisioningError,
            ProductStatus.Terminated,
            fail_provisioned_product_removal_command.FailProvisionedProductRemovalCommand,
        ),
        (
            ProductStatus.Running,
            ProductStatus.Provisioning,
            complete_product_launch_command.CompleteProductLaunchCommand,
        ),
        (
            ProductStatus.ProvisioningError,
            ProductStatus.Provisioning,
            fail_product_launch_command.FailProductLaunchCommand,
        ),
        (
            ProductStatus.Running,
            ProductStatus.Updating,
            complete_provisioned_product_update.CompleteProvisionedProductUpdateCommand,
        ),
        (
            ProductStatus.ProvisioningError,
            ProductStatus.Updating,
            fail_provisioned_product_update.FailProvisionedProductUpdateCommand,
        ),
        (
            ProductStatus.Running,
            ProductStatus.Starting,
            complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand,
        ),
        (
            ProductStatus.Stopped,
            ProductStatus.Stopping,
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
        ),
        (
            ProductStatus.ConfigurationFailed,
            ProductStatus.Provisioning,
            fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand,
        ),
        (
            ProductStatus.ConfigurationFailed,
            ProductStatus.Updating,
            fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand,
        ),
    ],
)
def test_from_event_should_map_to(new_status, old_status, expected_command, out_of_sync_event, sync_cmd_resolver):
    # ARRANGE
    event = out_of_sync_event(new_status, old_status)

    # ACT
    cmd = sync_cmd_resolver.from_sync_event(event)

    # ASSERT
    assertpy.assert_that(cmd).is_instance_of(expected_command)
