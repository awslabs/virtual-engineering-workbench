import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.provisioned_product_state import start
from app.provisioning.domain.commands.provisioned_product_state import start_provisioned_product_command
from app.provisioning.domain.events.provisioned_product_state import (
    provisioned_product_instance_started,
    provisioned_product_start_failed,
    provisioned_product_started,
)
from app.provisioning.domain.exceptions import insufficient_capacity_exception
from app.provisioning.domain.model import (
    connection_option,
    container_details,
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.value_objects import ip_address_value_object, provisioned_product_id_value_object


@freeze_time("2023-12-06")
@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True, False])
def test_start_virtual_target_should_start_virtual_target(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_parameter_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    authorize_user_ip_address_param_value,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        parameter_srv=mock_parameter_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    # ASSERT
    mock_instance_mgmt_srv.start_instance.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )
    if authorize_user_ip_address_param_value:
        for option in connection_option.ConnectionOption.list():
            for rule in connection_option.CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP[option]:
                mock_instance_mgmt_srv.authorize_user_ip_address.assert_any_call(
                    user_id="T0011AA",
                    aws_account_id="001234567890",
                    region="us-east-1",
                    connection_option=option,
                    ip_address="127.0.0.1/32",
                    port=rule.from_port,
                    to_port=rule.to_port,
                    protocol=rule.protocol.value,
                    user_sg_id="sg-12345",
                )
    else:
        mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_instance_started.ProvisionedProductInstanceStarted(provisionedProductId="pp-123")
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
@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True, False])
def test_start_virtual_target_in_already_running_state_should_publish_started_event_without_ec2_request(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_parameter_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    authorize_user_ip_address_param_value,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Running
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        parameter_srv=mock_parameter_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    # ASSERT
    if authorize_user_ip_address_param_value:
        for option in connection_option.ConnectionOption.list():
            for rule in connection_option.CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP[option]:
                mock_instance_mgmt_srv.authorize_user_ip_address.assert_any_call(
                    user_id="T0011AA",
                    aws_account_id="001234567890",
                    region="us-east-1",
                    connection_option=option,
                    ip_address="127.0.0.1/32",
                    port=rule.from_port,
                    to_port=rule.to_port,
                    protocol=rule.protocol.value,
                    user_sg_id="sg-12345",
                )
    else:
        mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()
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
        ),
    )


@freeze_time("2023-12-06")
@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True, False])
def test_start_virtual_target_in_stopping_state_should_publish_start_failed_event(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_parameter_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    authorize_user_ip_address_param_value,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    mock_instance_mgmt_srv.start_instance.return_value = product_status.EC2InstanceState.Stopping
    mock_instance_mgmt_srv.get_user_security_group_id.return_value = "sg-12345"

    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        parameter_srv=mock_parameter_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    # ASSERT
    mock_instance_mgmt_srv.start_instance.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )
    if authorize_user_ip_address_param_value:
        for option in connection_option.ConnectionOption.list():
            for rule in connection_option.CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP[option]:
                mock_instance_mgmt_srv.authorize_user_ip_address.assert_any_call(
                    user_id="T0011AA",
                    aws_account_id="001234567890",
                    region="us-east-1",
                    connection_option=option,
                    ip_address="127.0.0.1/32",
                    port=rule.from_port,
                    to_port=rule.to_port,
                    protocol=rule.protocol.value,
                    user_sg_id="sg-12345",
                )
    else:
        mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()
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
        ),
    )


@freeze_time("2023-12-06")
def test_start_virtual_target_should_catch_error(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_parameter_srv,
    mock_container_mgmt_srv,
):
    # ARRANGE
    mock_instance_mgmt_srv.start_instance.side_effect = insufficient_capacity_exception.InsufficientCapacityException(
        "test"
    )
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        parameter_srv=mock_parameter_srv,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=False,
    )

    # ASSERT
    mock_instance_mgmt_srv.start_instance.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        instance_id="i-01234567890abcdef",
        region="us-east-1",
    )

    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_start_failed.ProvisionedProductStartFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
            reason="INSUFFICIENT_INSTANCE_CAPACITY",
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
            status=product_status.ProductStatus.Stopped,
            statusReason="test",
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
@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True])
@pytest.mark.parametrize(
    ["product_current_status", "expected_product_status"],
    [
        (product_status.ProductStatus.Provisioning, product_status.ProductStatus.Running),
        (product_status.ProductStatus.Starting, product_status.ProductStatus.Running),
        (product_status.ProductStatus.Running, product_status.ProductStatus.Running),
    ],
)
def test_start_container_should_start_when_container_status_is_running(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_parameter_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    authorize_user_ip_address_param_value,
    mock_container_mgmt_srv,
    get_provisioned_product,
    product_current_status,
    expected_product_status,
):
    # ARRANGE
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    product = get_provisioned_product(
        status=product_current_status,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product

    mock_container_mgmt_srv.get_container_status.return_value = container_details.ContainerState(Name="STOPPED")
    mock_container_mgmt_srv.get_container_details.return_value = container_details.ContainerDetails(
        private_ip_address="127.0.0.1",
        state=container_details.ContainerState(Name="RUNNING"),
        task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
        name="cont123",
    )
    new_product = product
    new_product.status = expected_product_status

    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        parameter_srv=mock_parameter_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    # ASSERT
    mock_container_mgmt_srv.start_container.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        cluster_name="clust123",
        service_name="serv123",
    )
    if authorize_user_ip_address_param_value:
        for option in connection_option.ConnectionOption.list():
            for rule in connection_option.CONNECTION_OPTION_TO_SECURITY_GROUP_RULES_MAP[option]:
                mock_instance_mgmt_srv.authorize_user_ip_address.assert_any_call(
                    user_id="T0011AA",
                    aws_account_id="001234567890",
                    region="us-east-1",
                    connection_option="SSH",
                    ip_address="127.0.0.1/32",
                    port=22,
                    to_port=22,
                    protocol="tcp",
                    user_sg_id=None,
                )
    else:
        mock_instance_mgmt_srv.authorize_user_ip_address.assert_not_called()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_started.ProvisionedProductStarted(provisionedProductId="pp-123")
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_virtual_target_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        new_product,
    )


@freeze_time("2023-12-05")
@pytest.mark.parametrize(
    ["product_current_status", "expected_product_status"],
    [
        (product_status.ProductStatus.Provisioning, product_status.ProductStatus.Running),
        (product_status.ProductStatus.Starting, product_status.ProductStatus.Running),
        (product_status.ProductStatus.Running, product_status.ProductStatus.Running),
    ],
)
def test_start_container_should_continue_start_when_container_tasks_are_empty(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_parameter_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    mock_container_mgmt_srv,
    get_provisioned_product,
    product_current_status,
    expected_product_status,
):
    # ARRANGE
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    product = get_provisioned_product(
        status=product_current_status,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product

    mock_container_mgmt_srv.get_container_status.return_value = container_details.ContainerState(Name="STOPPED")
    mock_container_mgmt_srv.get_container_details.return_value = None

    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        parameter_srv=mock_parameter_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=True,
    )

    # ASSERT
    mock_container_mgmt_srv.start_container.assert_called_with(
        user_id="T0011AA",
        aws_account_id="001234567890",
        region="us-east-1",
        cluster_name="clust123",
        service_name="serv123",
    )
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()
    mock_virtual_target_repo.update_entity.assert_not_called()


@pytest.mark.parametrize("authorize_user_ip_address_param_value", [True])
def test_start_container_should_raise_insufficient_capacity_exception(
    mock_logger,
    mock_publisher,
    mock_instance_mgmt_srv,
    mock_parameter_srv,
    mock_virtual_targets_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_virtual_target_repo,
    authorize_user_ip_address_param_value,
    mock_container_mgmt_srv,
    get_provisioned_product,
):
    # ARRANGE
    command = start_provisioned_product_command.StartProvisionedProductCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
        user_ip_address=ip_address_value_object.from_str("127.0.0.1"),
    )
    product = get_provisioned_product(
        status=product_status.ProductStatus.Running,
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
    )
    mock_virtual_targets_qs.get_by_id.return_value = product
    mock_container_mgmt_srv.get_container_status.return_value = container_details.ContainerState(Name="STOPPED")

    # Mocking the start_container to raise InsufficientClusterCapacityException
    mock_container_mgmt_srv.start_container.side_effect = (
        insufficient_capacity_exception.InsufficientCapacityException()
    )

    # ACT
    start.handle(
        command=command,
        publisher=mock_publisher,
        virtual_targets_qs=mock_virtual_targets_qs,
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        parameter_srv=mock_parameter_srv,
        logger=mock_logger,
        spoke_account_vpc_id_param_name="/workbench/vpc/vpc-id",
        authorize_user_ip_address_param_value=authorize_user_ip_address_param_value,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_start_failed.ProvisionedProductStartFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.Container,
            owner="T0011AA",
            reason="INSUFFICIENT_CLUSTER_CAPACITY",
        )
    )
