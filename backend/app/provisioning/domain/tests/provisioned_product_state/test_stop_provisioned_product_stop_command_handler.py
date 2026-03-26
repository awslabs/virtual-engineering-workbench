from freezegun import freeze_time

from app.provisioning.domain.command_handlers.provisioned_product_state import stop
from app.provisioning.domain.commands.provisioned_product_state import stop_provisioned_product_command
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_instance_stopped,
    provisioned_product_stop_failed,
    provisioned_product_stopped,
)
from app.provisioning.domain.model import container_details, product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@freeze_time("2023-12-06")
def test_stop_virtual_target_should_stop_virtual_target(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Running
    # ACT
    stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.stop_instance.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_instance_stopped.ProvisionedProductInstanceStopped(provisionedProductId="pp-123")
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
        ),
    )


@freeze_time("2023-12-06")
def test_stop_virtual_target_in_already_stopped_state_should_publish_stopped_event_without_ec2_request(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )

    # ACT
    stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stopped.ProvisionedProductStopped(provisionedProductId="pp-123")
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
            status=product_status.ProductStatus.Stopped,
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
        ),
    )


@freeze_time("2023-12-06")
def test_stop_virtual_target_in_starting_state_should_publish_stop_failed_event(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Running
    mock_instance_mgmt_srv.stop_instance.return_value = product_status.EC2InstanceState.Pending

    # ACT
    stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.stop_instance.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_failed.ProvisionedProductStopFailed(provisionedProductId="pp-123")
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
            status=product_status.ProductStatus.Starting,
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
        ),
    )


# Container Tests


@freeze_time("2023-12-05")
def test_stop_container_should_stop_container_when_status_returns_stopped(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    product = get_provisioned_product(
        status=product_status.ProductStatus.Running,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product
    mock_container_mgmt_srv.get_container_details.side_effect = [
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="RUNNING"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="STOPPED"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
    ]
    # ACT
    stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_container_mgmt_srv.stop_container.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        cluster_name="clust123",
        service_name="serv123",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_instance_stopped.ProvisionedProductInstanceStopped(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Stopped,
            provision_product_type=provisioned_product.ProvisionedProductType.Container,
        ),
    )


@freeze_time("2023-12-05")
def test_stop_container_should_stop_container_when_status_returns_deprovisioning(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    product = get_provisioned_product(
        status=product_status.ProductStatus.Running,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product
    mock_container_mgmt_srv.get_container_details.side_effect = [
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="RUNNING"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="DEPROVISIONING"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
    ]
    # ACT
    stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_container_mgmt_srv.stop_container.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        cluster_name="clust123",
        service_name="serv123",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_instance_stopped.ProvisionedProductInstanceStopped(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            status=product_status.ProductStatus.Stopping,
            provision_product_type=provisioned_product.ProvisionedProductType.Container,
        ),
    )


@freeze_time("2023-12-05")
def test_stop_container_should_stop_container_when_status_is_stopped(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    product = get_provisioned_product(
        status=product_status.ProductStatus.Stopped,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product
    mock_container_mgmt_srv.get_container_details.side_effect = [
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="STOPPED"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="STOPPED"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
    ]
    # ACT
    stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stopped.ProvisionedProductStopped(provisionedProductId="pp-123")
    )


@freeze_time("2023-12-05")
def test_stop_container_should_fail_container_when_status_isnt_expected(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = stop_provisioned_product_command.StopProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    product = get_provisioned_product(
        status=product_status.ProductStatus.Running,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product
    mock_container_mgmt_srv.get_container_details.side_effect = [
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="RUNNING"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="RUNNING"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
    ]
    # ACT
    stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_failed.ProvisionedProductStopFailed(provisionedProductId="pp-123")
    )
