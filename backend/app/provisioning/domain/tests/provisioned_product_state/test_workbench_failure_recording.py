"""a failed start records why, and the next start clears it."""

import assertpy
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.provisioned_product_state import complete_start, initiate_start, start
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    initiate_provisioned_product_start_command,
    start_provisioned_product_command,
)
from app.provisioning.domain.events.provisioned_product_state import provisioned_product_start_failed
from app.provisioning.domain.exceptions import instance_start_exception
from app.provisioning.domain.model import instance_details, product_status
from app.provisioning.domain.value_objects import (
    ip_address_value_object,
    project_id_value_object,
    provisioned_product_id_value_object,
    user_id_value_object,
)


def _saved(mock_virtual_target_repo):
    call = mock_virtual_target_repo.update_entity.call_args
    return call.kwargs["entity"] if "entity" in call.kwargs else call.args[1]


@freeze_time("2023-12-06")
def test_a_refused_start_records_the_ec2_reason(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_virtual_target_repo,
    mock_parameter_srv,
    mock_container_mgmt_srv,
):
    mock_instance_mgmt_srv.start_instance.side_effect = instance_start_exception.InstanceStartException(
        "VcpuLimitExceeded: You have requested more vCPU capacity than your current vCPU limit of 0 allows."
    )

    start.handle(
        command=start_provisioned_product_command.StartProvisionedProductCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
            user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        ),
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    saved = _saved(mock_virtual_target_repo)
    assertpy.assert_that(saved.status).is_equal_to(product_status.ProductStatus.Stopped)
    assertpy.assert_that(saved.statusReason).starts_with("VcpuLimitExceeded")
    assertpy.assert_that(saved.failedOperation).is_equal_to("START")
    event = mock_message_bus.publish.call_args.args[0]
    assertpy.assert_that(event.reason).is_equal_to(
        provisioned_product_start_failed.StartFailedReason.InstanceStartError
    )


@freeze_time("2023-12-06")
def test_a_new_start_clears_the_last_failure(
    mock_logger,
    mock_publisher,
    mock_virtual_targets_qs,
    mock_virtual_target_repo,
    get_virtual_target,
):
    stopped = get_virtual_target(status=product_status.ProductStatus.Stopped)
    stopped.statusReason = "Insufficient instance capacity error"
    stopped.failedOperation = "START"
    mock_virtual_targets_qs.get_by_id.return_value = stopped

    initiate_start.handle(
        command=initiate_provisioned_product_start_command.InitiateProvisionedProductStartCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
            user_id=user_id_value_object.from_str("T0011AA"),
            project_id=project_id_value_object.from_str("proj-123"),
            user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
        ),
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        logger=mock_logger,
    )

    saved = _saved(mock_virtual_target_repo)
    assertpy.assert_that(saved.status).is_equal_to(product_status.ProductStatus.Starting)
    assertpy.assert_that(saved.statusReason).is_none()
    assertpy.assert_that(saved.failedOperation).is_none()


@freeze_time("2023-12-06")
def test_a_start_that_ends_stopped_records_the_instance_state_reason(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_virtual_target_repo,
    get_virtual_target,
    mock_container_mgmt_srv,
):
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Starting)
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Stopped),
        PrivateIpAddress="192.168.1.1",
    )
    mock_instance_mgmt_srv.get_instance_state_reason.return_value = (
        "Server.InsufficientInstanceCapacity: Insufficient capacity."
    )

    complete_start.handle(
        command=complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        ),
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    saved = _saved(mock_virtual_target_repo)
    assertpy.assert_that(saved.status).is_equal_to(product_status.ProductStatus.Stopped)
    assertpy.assert_that(saved.statusReason).is_equal_to("Server.InsufficientInstanceCapacity: Insufficient capacity.")
    assertpy.assert_that(saved.failedOperation).is_equal_to("START")


@freeze_time("2023-12-06")
def test_a_successful_start_clears_the_last_failure(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_virtual_target_repo,
    get_virtual_target,
    mock_container_mgmt_srv,
):
    starting = get_virtual_target(status=product_status.ProductStatus.Starting)
    starting.statusReason = "Insufficient instance capacity error"
    starting.failedOperation = "START"
    mock_virtual_targets_qs.get_by_id.return_value = starting
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
        PrivateIpAddress="192.168.1.1",
    )

    complete_start.handle(
        command=complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
            provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        ),
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    saved = _saved(mock_virtual_target_repo)
    assertpy.assert_that(saved.status).is_equal_to(product_status.ProductStatus.Running)
    assertpy.assert_that(saved.statusReason).is_none()
    assertpy.assert_that(saved.failedOperation).is_none()
