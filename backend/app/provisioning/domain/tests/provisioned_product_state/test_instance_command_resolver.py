import assertpy
import pytest

from app.provisioning.domain.commands.product_provisioning import update_provisioned_product_command
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
)
from app.provisioning.domain.model import product_status
from app.provisioning.domain.orchestration import instance_command_resolver


@pytest.fixture
def instance_cmd_resolver():
    return instance_command_resolver.init()


@pytest.mark.parametrize(
    "new_ec2_state,old_status,expected_command",
    [
        (
            product_status.EC2InstanceState.Stopped,
            product_status.ProductStatus.Updating,
            update_provisioned_product_command.UpdateProvisionedProductCommand,
        ),
        (
            product_status.EC2InstanceState.Stopped,
            product_status.ProductStatus.Stopping,
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
        ),
        (
            product_status.EC2InstanceState.Running,
            product_status.ProductStatus.Starting,
            complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand,
        ),
    ],
)
def test_from_ec2_state_should_map_to(
    new_ec2_state, old_status, expected_command, instance_cmd_resolver, get_virtual_target
):
    # ARRANGE
    pp = get_virtual_target(status=old_status)

    # ACT
    cmd = instance_cmd_resolver.from_ec2_state(provisioned_product=pp, ec2_state=new_ec2_state)

    # ASSERT
    assertpy.assert_that(cmd).is_instance_of(expected_command)
