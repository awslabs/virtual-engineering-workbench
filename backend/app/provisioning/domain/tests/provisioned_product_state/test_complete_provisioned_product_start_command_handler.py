import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.provisioned_product_state import complete_start
from app.provisioning.domain.commands.provisioned_product_state import complete_provisioned_product_start_command
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_start_failed,
    provisioned_product_started,
)
from app.provisioning.domain.model import (
    container_details,
    instance_details,
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@freeze_time("2023-12-06")
def test_complete_provisioned_product_start_should_complete_virtual_target_start(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    get_virtual_target,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
        PrivateIpAddress="192.168.1.1",
    )
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Starting)

    # ACT
    complete_start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_started.ProvisionedProductStarted(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName="my name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Running,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=None,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            privateIp="192.168.1.1",
            startDate="2023-12-06T00:00:00+00:00",
        ),
    )


@freeze_time("2023-12-06")
def test_complete_provisioned_product_start_in_stopping_state_should_publish_start_failed_event(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    get_virtual_target,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Stopping),
        PrivateIpAddress="192.168.1.1",
    )
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Starting)

    # ACT
    complete_start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_start_failed.ProvisionedProductStartFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName="my name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.Stopping,
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=None,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            privateIp="192.168.1.1",
        ),
    )


@freeze_time("2023-12-06")
def test_complete_provisioned_product_start_should_ignore_when_pp_is_not_in_required_state(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    get_virtual_target,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Terminated)

    # ACT
    complete_start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.get_instance_state.assert_not_called()
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-06")
def test_complete_provisioned_product_start_should_update_ip_addresses(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    get_virtual_target,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
        PrivateIpAddress="192.168.2.1",
        PublicIpAddress="192.168.2.2",
    )
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Starting)

    # ACT
    complete_start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.get_instance_details.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )

    updated_entity = mock_virtual_target_repo.update_entity.call_args.kwargs.get("entity")
    assertpy.assert_that(updated_entity.privateIp).is_equal_to("192.168.2.1")
    assertpy.assert_that(updated_entity.publicIp).is_equal_to("192.168.2.2")


@freeze_time("2023-12-05")
@pytest.mark.parametrize(
    "current_product_status",
    [
        product_status.ProductStatus.Starting,
        product_status.ProductStatus.Provisioning,
        product_status.ProductStatus.Running,
    ],
)
def test_complete_provisioned_product_start_should_complete_container_start(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    get_virtual_target,
    mock_container_mgmt_srv,
    get_provisioned_product,
    current_product_status,
):
    # ARRANGE
    command = complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    product = get_provisioned_product(
        status=current_product_status,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product
    mock_container_mgmt_srv.get_container_details.return_value = container_details.ContainerDetails(
        State=container_details.ContainerState(Name="RUNNING"),
        PrivateIpAddress="192.168.1.1",
        task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
        name="cont123",
    )
    # ACT
    complete_start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_started.ProvisionedProductStarted(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Running,
            provision_product_type=provisioned_product.ProvisionedProductType.Container,
            private_ip="192.168.1.1",
            start_date="2023-12-05T00:00:00+00:00",
        ),
    )
