from freezegun import freeze_time

from app.provisioning.domain.command_handlers.provisioned_product_state import complete_stop
from app.provisioning.domain.commands.provisioned_product_state import complete_provisioned_product_stop_command
from app.provisioning.domain.events.product_provisioning import (
    provisioned_product_stop_for_upgrade_failed,
    provisioned_product_stopped_for_upgrade,
)
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_stop_failed,
    provisioned_product_stopped,
)
from app.provisioning.domain.model import container_details, product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@freeze_time("2023-12-06")
def test_complete_virtual_target_stop_should_complete_virtual_target_stop(
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
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Starting)

    # ACT
    complete_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.get_instance_state.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )

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
def test_complete_virtual_target_in_starting_state_should_publish_stop_failed_event(
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
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Pending
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Starting)

    # ACT
    complete_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.get_instance_state.assert_called_with(
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


@freeze_time("2023-12-06")
def test_complete_virtual_target_stop_should_ignore_when_pp_is_not_in_required_state(
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
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(
        status=product_status.ProductStatus.Provisioning
    )

    # ACT
    complete_stop.handle(
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
def test_complete_virtual_target_stop_should_trigger_product_update_if_instance_stopped(
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
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Updating)

    # ACT
    complete_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.get_instance_state.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stopped_for_upgrade.ProvisionedProductStoppedForUpgrade(
            provisionedProductId=command.provisioned_product_id.value
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
            status=product_status.ProductStatus.Updating,
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
def test_complete_virtual_target_stop_should_trigger_product_update_fail_if_instance_not_stopped(
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
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Pending
    mock_virtual_targets_qs.get_by_id.return_value = get_virtual_target(status=product_status.ProductStatus.Updating)

    # ACT
    complete_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_instance_mgmt_srv.get_instance_state.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stop_for_upgrade_failed.ProvisionedProductStopForUpgradeFailed(
            provisionedProductId=command.provisioned_product_id.value
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
            status=product_status.ProductStatus.Updating,
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
def test_complete_virtual_target_stop_should_complete_container_stop(
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
):
    # ARRANGE
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )

    mock_virtual_targets_qs.get_by_id.return_value = get_provisioned_product(
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
        status=product_status.ProductStatus.Starting,
    )
    mock_container_mgmt_srv.get_container_details.side_effect = [
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="STOPPED"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
    ]

    # ACT
    complete_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_container_mgmt_srv.get_container_details.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        cluster_name="clust123",
        service_name="serv123",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stopped.ProvisionedProductStopped(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            provision_product_type=provisioned_product.ProvisionedProductType.Container,
            status=product_status.ProductStatus.Stopped,
        ),
    )


@freeze_time("2023-12-05")
def test_container_stop_should_complete_container_when_no_task_exists(
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
):
    # ARRANGE
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )

    mock_virtual_targets_qs.get_by_id.return_value = get_provisioned_product(
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
        status=product_status.ProductStatus.Starting,
    )
    mock_container_mgmt_srv.get_container_details.return_value = None

    # ACT
    complete_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_container_mgmt_srv.get_container_details.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        cluster_name="clust123",
        service_name="serv123",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_stopped.ProvisionedProductStopped(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        get_provisioned_product(
            provision_product_type=provisioned_product.ProvisionedProductType.Container,
            status=product_status.ProductStatus.Stopped,
        ),
    )


@freeze_time("2023-12-05")
def test_complete_virtual_target_stop_should_fail_container_stop(
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
):
    # ARRANGE
    command = complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )

    mock_virtual_targets_qs.get_by_id.return_value = get_provisioned_product(
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
        status=product_status.ProductStatus.Starting,
    )
    mock_container_mgmt_srv.get_container_details.side_effect = [
        container_details.ContainerDetails(
            private_ip_address="127.0.0.1",
            state=container_details.ContainerState(Name="RUNNING"),
            task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
            name="cont123",
        ),
    ]

    # ACT
    complete_stop.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
    )

    # ASSERT
    mock_container_mgmt_srv.get_container_details.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        cluster_name="clust123",
        service_name="serv123",
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
        get_provisioned_product(
            provision_product_type=provisioned_product.ProvisionedProductType.Container,
            status=product_status.ProductStatus.Running,
        ),
    )
