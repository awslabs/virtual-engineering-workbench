import assertpy
import pytest

from app.provisioning.domain.commands.product_provisioning import update_provisioned_product_command
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
)
from app.provisioning.domain.model import product_status
from app.provisioning.domain.orchestration import container_command_resolver


@pytest.fixture
def container_cmd_resolver():
    return container_command_resolver.init()


@pytest.mark.parametrize(
    "new_container_state,old_status,expected_command",
    [
        (
            product_status.TaskState.Stopped,
            product_status.ProductStatus.Updating,
            update_provisioned_product_command.UpdateProvisionedProductCommand,
        ),
        (
            product_status.TaskState.Stopped,
            product_status.ProductStatus.Stopping,
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
        ),
        (
            product_status.TaskState.Stopping,
            product_status.ProductStatus.Stopping,
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
        ),
        (
            product_status.TaskState.Deprovisioning,
            product_status.ProductStatus.Stopping,
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
        ),
        (
            product_status.TaskState.Running,
            product_status.ProductStatus.Starting,
            complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand,
        ),
    ],
)
def test_from_container_state_should_map_to(
    new_container_state, old_status, expected_command, container_cmd_resolver, get_virtual_target
):
    # ARRANGE
    pp = get_virtual_target(status=old_status)
    # ACT
    cmd = container_cmd_resolver.from_container_state(provisioned_product=pp, container_state=new_container_state)

    # ASSERT
    assertpy.assert_that(cmd).is_instance_of(expected_command)
