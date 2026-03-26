from unittest import mock

import assertpy
import pytest
from freezegun import freeze_time

from app.provisioning.domain.command_handlers.product_provisioning import complete_launch
from app.provisioning.domain.commands.product_provisioning import complete_product_launch_command
from app.provisioning.domain.events.product_provisioning import product_launch_failed, product_launched
from app.provisioning.domain.events.provisioned_product_configuration import provisioned_product_configuration_requested
from app.provisioning.domain.model import (
    additional_configuration,
    block_device_mappings,
    container_details,
    instance_details,
    product_status,
    provisioned_product,
    provisioned_product_output,
    provisioning_parameter,
)
from app.provisioning.domain.ports import instance_management_service, versions_query_service
from app.provisioning.domain.read_models import product, version
from app.provisioning.domain.tests.product_provisioning.conftest import TEST_COMPONENT_VERSION_DETAILS, TEST_OS_VERSION
from app.provisioning.domain.value_objects import provisioned_product_id_value_object


@pytest.fixture()
def mock_instance_mgmt_service(get_test_block_device_mappings):
    svc = mock.create_autospec(spec=instance_management_service.InstanceManagementService)
    svc.get_instance_state.return_value = "running"
    svc.get_instance_platform.return_value = "Windows"
    svc.get_block_device_mappings.return_value = get_test_block_device_mappings()
    svc.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
        PrivateIpAddress="192.168.1.1",
    )
    return svc


def get_mocked_block_device_mappings():
    return block_device_mappings.BlockDeviceMappings(
        rootDeviceName="/dev/sda1",
        mappings=[
            block_device_mappings.BlockDevice(deviceName="/dev/sda1", volumeId="vol-1234567890"),
            block_device_mappings.BlockDevice(deviceName="/dev/sdb", volumeId="vol-0987654321"),
        ],
    )


def get_mocked_product_version(
    region: str = "us-east-1",
    stage: version.VersionStage = version.VersionStage.DEV,
    sc_product_id: str = "sc-prod-123",
    sc_provisioning_artifact_id: str = "sc-pa-123",
    aws_account_id: str = "001234567890",
    version_name: str = "1.1.0",
    version_id: str = "ver-456",
):
    return version.Version(
        projectId="proj-123",
        productId="prod-123",
        technologyId="tech-123",
        versionId=version_id,
        versionName=version_name,
        versionDescription="Initial release",
        awsAccountId=aws_account_id,
        accountId="acc-123",
        stage=stage,
        region=region,
        amiId="ami-123",
        scProductId=sc_product_id,
        scProvisioningArtifactId=sc_provisioning_artifact_id,
        isRecommendedVersion=True,
        parameters=[
            version.VersionParameter(
                parameterKey="SomeParam",
                defaultValue="some-default",
                parameterType="String",
            ),
            version.VersionParameter(
                parameterKey="SomeTechParam",
                defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                parameterType="AWS::SSM::Parameter::Value<String>",
            ),
        ],
        lastUpdateDate="2023-12-05",
        componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
        osVersion=TEST_OS_VERSION,
    )


def get_mocked_product_version_for_container(
    region: str = "us-east-1",
    stage: version.VersionStage = version.VersionStage.DEV,
    sc_product_id: str = "sc-prod-123",
    sc_provisioning_artifact_id: str = "sc-pa-123",
    aws_account_id: str = "001234567890",
    version_name: str = "1.1.0",
    version_id: str = "ver-456",
):
    return version.Version(
        projectId="proj-123",
        productId="prod-123",
        technologyId="tech-123",
        versionId=version_id,
        versionName=version_name,
        versionDescription="Initial release",
        awsAccountId=aws_account_id,
        accountId="acc-123",
        stage=stage,
        region=region,
        amiId=None,
        containerName="cont123",
        scProductId=sc_product_id,
        scProvisioningArtifactId=sc_provisioning_artifact_id,
        isRecommendedVersion=True,
        parameters=[
            version.VersionParameter(
                parameterKey="SomeParam",
                defaultValue="some-default",
                parameterType="String",
            ),
            version.VersionParameter(
                parameterKey="SomeTechParam",
                defaultValue="/workbench/autosar/adaptive/ami-id/v1-3-x",
                parameterType="AWS::SSM::Parameter::Value<String>",
            ),
        ],
        lastUpdateDate="2023-12-05",
        componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
        osVersion=TEST_OS_VERSION,
    )


@pytest.fixture()
def mock_versions_query_service():
    qs_mock = mock.create_autospec(spec=versions_query_service.VersionsQueryService)
    qs_mock.get_product_version_distributions.return_value = [
        get_mocked_product_version(
            region="us-east-1",
            stage=version.VersionStage.DEV,
            sc_product_id="sc-prod-123",
            sc_provisioning_artifact_id="sc-pa-123",
            aws_account_id="001234567890",
        )
    ]
    return qs_mock


def get_mock_provisioned_product(
    version_name: str = "1.0.0",
    version_id: str = "vers-123",
    new_vers_id: str = None,
    new_vers_name: str = None,
    block_device_mappings: block_device_mappings.BlockDeviceMappings = None,
    public_ip: str | None = None,
    outputs: list[provisioned_product_output.ProvisionedProductOutput] = [
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="instance-id", outputValue="i-1234567890", description="description"
        ),
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="privateIp", outputValue="192.168.1.1", description="description"
        ),
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="SSHKeyPair",
            outputValue="/ec2/keypair/i-123",
            description="SSM Parameter containing the ssh key generated",
        ),
    ],
    availability_zones_triggered: list[str] | None = None,
    user_ip_address: str | None = None,
):
    return provisioned_product.ProvisionedProduct.construct(
        projectId="proj-123",
        provisionedProductId="pp-123",
        provisionedProductName=mock.ANY,
        provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
        userId="T0011AA",
        userDomains=["domain"],
        status=product_status.ProductStatus.Running,
        productId="prod-123",
        productName="Pied Piper",
        productDescription="Compression",
        technologyId="tech-123",
        versionId=version_id,
        versionName=version_name,
        awsAccountId="001234567890",
        accountId="acc-123",
        stage=provisioned_product.ProvisionedProductStage.DEV,
        region="us-east-1",
        amiId="ami-123",
        scProductId="sc-prod-123",
        scProvisioningArtifactId="sc-pa-123",
        scProvisionedProductId="pp-123",
        provisioningParameters=[
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
        ],
        createDate="2023-12-05T00:00:00+00:00",
        lastUpdateDate="2023-12-06T00:00:00+00:00",
        startDate="2023-12-06T00:00:00+00:00",
        createdBy="T0011AA",
        lastUpdatedBy="T0011AA",
        outputs=outputs,
        privateIp="192.168.1.1",
        publicIp=public_ip,
        instanceId="i-1234567890",
        sshKeyPath="/ec2/keypair/i-123",
        newVersionName=new_vers_name if new_vers_name else None,
        newVersionId=new_vers_id if new_vers_id else None,
        upgradeAvailable=True if new_vers_name else False,
        blockDeviceMappings=block_device_mappings,
        availabilityZonesTriggered=availability_zones_triggered,
        userIpAddress=user_ip_address,
    )


@freeze_time("2023-12-06")
@pytest.mark.parametrize(
    "version_distributions,pproduct",
    [
        (
            [
                get_mocked_product_version(
                    region="us-east-1",
                    stage=version.VersionStage.DEV,
                    sc_product_id="sc-prod-123",
                    sc_provisioning_artifact_id="sc-pa-123",
                    aws_account_id="001234567890",
                )
            ],
            get_mock_provisioned_product(
                block_device_mappings=get_mocked_block_device_mappings(), public_ip="192.168.1.2"
            ),
        ),
        (
            [
                get_mocked_product_version(
                    region="us-east-1",
                    stage=version.VersionStage.DEV,
                    sc_product_id="sc-prod-123",
                    sc_provisioning_artifact_id="sc-pa-123",
                    aws_account_id="001234567890",
                ),
                get_mocked_product_version(
                    region="us-east-1",
                    stage=version.VersionStage.DEV,
                    sc_product_id="sc-prod-123",
                    sc_provisioning_artifact_id="sc-pa-123",
                    aws_account_id="001234567890",
                    version_name="1.2.0",
                    version_id="vers-456",
                ),
            ],
            get_mock_provisioned_product(
                new_vers_name="1.2.0",
                new_vers_id="vers-456",
                block_device_mappings=get_mocked_block_device_mappings(),
                public_ip="192.168.1.2",
            ),
        ),
    ],
)
def test_complete_provisioned_product_launch_should_update_attributes_and_publish(
    version_distributions,
    pproduct,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    get_test_product,
    mock_products_repo,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    mock_versions_query_service.get_product_version_distributions.return_value = version_distributions
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(sc_provisioned_product_id="pp-123")

    mock_products_qs.get_product.return_value = get_test_product()
    mock_instance_mgmt_service.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
        PrivateIpAddress="192.168.1.1",
        PublicIpAddress="192.168.1.2",
    )

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launched.ProductLaunched(
            projectId="proj-123",
            provisionedProductId="pp-123",
            owner="T0011AA",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            privateIP="192.168.1.1",
            instanceId="i-1234567890",
            awsAccountId="001234567890",
            region="us-east-1",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        pproduct,
    )
    mock_products_qs.get_product.assert_called_once_with(project_id="proj-123", product_id="prod-123")


@freeze_time("2023-12-05")
def test_complete_provisioned_product_launch_should_update_attributes_and_publish_for_container(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    get_test_product,
    mock_products_repo,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    mock_versions_query_service.get_product_version_distributions.return_value = [
        get_mocked_product_version_for_container(
            region="us-east-1",
            stage=version.VersionStage.DEV,
            sc_product_id="sc-prod-123",
            sc_provisioning_artifact_id="sc-pa-123",
            aws_account_id="001234567890",
        )
    ]

    mock_container_mgmt_srv.get_container_details.return_value = container_details.ContainerDetails(
        state=container_details.ContainerState(Name=product_status.TaskState.Pending),
        private_ip_address="192.168.1.1",
        task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
        name="cont123",
    )

    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    outputs = [
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="ClusterName", outputValue="clust123", description="description"
        ),
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="ServiceName", outputValue="serv123", description="description"
        ),
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="SSHKeyPair",
            outputValue="/ec2/keypair/i-123",
            description="SSM Parameter containing the ssh key generated",
        ),
    ]
    pv_product = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
        provision_product_type=provisioned_product.ProvisionedProductType.Container,
        private_ip="192.168.1.1",
        upgrade_available=False,
        outputs=outputs,
    )
    pv_product.startDate = "2023-12-05T00:00:00+00:00"

    mock_provisioned_products_qs.get_by_id.return_value = pv_product

    mock_products_srv.get_provisioned_product_outputs.return_value = outputs

    mock_products_qs.get_product.return_value = get_test_product(product_type=product.ProductType.Container)

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launched.ProductLaunched(
            projectId="proj-123",
            provisionedProductId="pp-123",
            owner="T0011AA",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.Container,
            privateIP="192.168.1.1",
            serviceId="serv123",
            awsAccountId="001234567890",
            region="us-east-1",
            containerTaskArn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        pv_product,
    )
    mock_products_qs.get_product.assert_called_once_with(project_id="proj-123", product_id="prod-123")


def test_complete_provisioned_product_lauch_when_contains_secret_name_should_store_in_the_entity(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    get_test_product,
    mock_products_repo,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    mock_versions_query_service.get_product_version_distributions.return_value = [
        get_mocked_product_version(
            region="us-east-1",
            stage=version.VersionStage.DEV,
            sc_product_id="sc-prod-123",
            sc_provisioning_artifact_id="sc-pa-123",
            aws_account_id="001234567890",
        )
    ]
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(sc_provisioned_product_id="sc-pp-123")
    mock_products_srv.get_provisioned_product_outputs.return_value = [
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="instance-id", outputValue="i-1234567890", description="description"
        ),
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="UserCredentialsSecret",
            outputValue="UserCredentialSecretName",
            description="Secrets Manager secret containing user name and password",
        ),
    ]

    mock_products_qs.get_product.return_value = get_test_product()
    mock_instance_mgmt_service.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
        PrivateIpAddress="192.168.1.1",
    )

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    stored_provisioned_product = mock_provisioned_product_repo.update_entity.call_args.kwargs.get("entity")
    assertpy.assert_that(stored_provisioned_product.userCredentialName).is_equal_to("UserCredentialSecretName")


@pytest.mark.parametrize(
    "provisioned_product_status",
    [s for s in product_status.ProductStatus if s != product_status.ProductStatus.Provisioning],
)
def test_complete_provisioned_product_launch_when_status_not_provisioning_should_ignore(
    provisioned_product_status,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
        status=provisioned_product_status,
    )

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_not_called()
    mock_unit_of_work.commit.assert_not_called()


@freeze_time("2023-12-06")
def test_complete_provisioned_product_launch_when_no_ip_in_the_instance_should_fail(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(sc_provisioned_product_id="pp-123")
    mock_products_srv.get_provisioned_product_outputs.return_value = [
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="instance-id", outputValue="i-1234567890", description="description"
        ),
    ]
    mock_instance_mgmt_service.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Stopped),
    )

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.ProvisioningError,
            statusReason="Missing IP address in the output.",
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="instance-id", outputValue="i-1234567890", description="description"
                ),
            ],
            instanceId="i-1234567890",
        ),
    )


@freeze_time("2023-12-06")
def test_complete_provisioned_product_launch_when_no_instance_id_in_the_outputs_should_fail(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    mock_versions_query_service,
    publishing_qry_svc_mock,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
    )
    mock_products_srv.get_provisioned_product_outputs.return_value = [
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="privateIp", outputValue="192.168.1.1", description="description"
        ),
    ]

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.ProvisioningError,
            statusReason="Missing virtual target instance ID in the output.",
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="privateIp", outputValue="192.168.1.1", description="description"
                )
            ],
            privateIp=None,
            containerName=None,
            containerTaskArn=None,
        ),
    )


@freeze_time("2023-12-06")
def test_complete_provisioned_product_launch_when_catalog_api_fails_should_fail_and_publish(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
    )

    mock_products_srv.get_provisioned_product_outputs.side_effect = [Exception("failed")]

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT

    mock_message_bus.publish.assert_called_once_with(
        product_launch_failed.ProductLaunchFailed(
            projectId="proj-123",
            provisionedProductId="pp-123",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            owner="T0011AA",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        provisioned_product.ProvisionedProduct.construct(
            projectId="proj-123",
            provisionedProductId="pp-123",
            provisionedProductName=mock.ANY,
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=product_status.ProductStatus.ProvisioningError,
            statusReason="failed",
            productId="prod-123",
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId="i-01234567890abcdef",
            stage=provisioned_product.ProvisionedProductStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId="pp-123",
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-06T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        ),
    )


@freeze_time("2023-12-05")
def test_complete_provisioned_product_launch_updates_product_stats(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    get_test_product,
    mock_products_repo,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
    )

    mock_products_qs.get_product.return_value = get_test_product(average_provisioning_time=10, total_reported_times=1)

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_products_qs.get_product.assert_called_once_with(project_id="proj-123", product_id="prod-123")
    mock_products_repo.update_entity.assert_called_once_with(
        product.ProductPrimaryKey(projectId="proj-123", productId="prod-123"),
        product.Product(
            projectId="proj-123",
            productId="prod-123",
            technologyId="t-123",
            technologyName="test tech",
            productName="Pied Piper",
            productType=product.ProductType.VirtualTarget,
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            averageProvisioningTime=5,
            totalReportedTimes=2,
        ),
    )
    mock_unit_of_work.commit.assert_called_once()


@freeze_time("2023-12-05")
def test_complete_provisioned_product_launch_should_publish_configuration_request_when_additional_configuration_needed(
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    get_test_product,
    mock_products_repo,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123",
        additional_configurations=[
            additional_configuration.AdditionalConfiguration(
                type=additional_configuration.ProvisionedProductConfigurationTypeEnum.VVPLProvisionedProductConfiguration,
                parameters=[
                    additional_configuration.AdditionalConfigurationParameter(key="param-1", value="value-1"),
                    additional_configuration.AdditionalConfigurationParameter(key="param-2", value="value-2"),
                ],
            )
        ],
    )

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_unit_of_work.commit.assert_called_once()
    mock_message_bus.publish.assert_called_once_with(
        provisioned_product_configuration_requested.ProvisionedProductConfigurationRequested(
            provisionedProductId="pp-123",
        )
    )


@freeze_time("2023-12-06")
@pytest.mark.parametrize(
    "version_distributions,pproduct",
    [
        (
            [
                get_mocked_product_version(
                    region="us-east-1",
                    stage=version.VersionStage.DEV,
                    sc_product_id="sc-prod-123",
                    sc_provisioning_artifact_id="sc-pa-123",
                    aws_account_id="001234567890",
                )
            ],
            get_mock_provisioned_product(
                block_device_mappings=get_mocked_block_device_mappings(),
                public_ip="192.168.1.2",
            ),
        )
    ],
)
def test_complete_provisioned_product_launch_should_remove_azs_attribute_and_publish(
    version_distributions,
    pproduct,
    mock_logger,
    mock_publisher,
    mock_products_srv,
    mock_provisioned_products_qs,
    mock_message_bus,
    mock_unit_of_work,
    mock_provisioned_product_repo,
    mock_instance_mgmt_service,
    get_provisioned_product,
    mock_products_qs,
    get_test_product,
    mock_products_repo,
    mock_versions_query_service,
    mock_container_mgmt_srv,
):
    # ARRANGE
    mock_versions_query_service.get_product_version_distributions.return_value = version_distributions
    command = complete_product_launch_command.CompleteProductLaunchCommand(
        provisioned_product_id=provisioned_product_id_value_object.from_str("pp-123"),
    )
    mock_provisioned_products_qs.get_by_id.return_value = get_provisioned_product(
        sc_provisioned_product_id="pp-123", availability_zones_triggered=["az-1", "az-2"]
    )

    mock_products_qs.get_product.return_value = get_test_product()
    mock_instance_mgmt_service.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
        PrivateIpAddress="192.168.1.1",
        PublicIpAddress="192.168.1.2",
    )

    # ACT
    complete_launch.handle(
        command=command,
        publisher=mock_publisher,
        provisioned_products_qs=mock_provisioned_products_qs,
        products_srv=mock_products_srv,
        instance_mgmt_srv=mock_instance_mgmt_service,
        container_mgmt_srv=mock_container_mgmt_srv,
        logger=mock_logger,
        products_qry_srv=mock_products_qs,
        versions_qry_srv=mock_versions_query_service,
    )

    # ASSERT
    mock_message_bus.publish.assert_called_once_with(
        product_launched.ProductLaunched(
            projectId="proj-123",
            provisionedProductId="pp-123",
            owner="T0011AA",
            productName="Pied Piper",
            productType=provisioned_product.ProvisionedProductType.VirtualTarget,
            privateIP="192.168.1.1",
            instanceId="i-1234567890",
            awsAccountId="001234567890",
            region="us-east-1",
        )
    )
    mock_unit_of_work.commit.assert_called_once()
    mock_provisioned_product_repo.update_entity.assert_called_once_with(
        provisioned_product.ProvisionedProductPrimaryKey(
            projectId="proj-123",
            provisionedProductId="pp-123",
        ),
        pproduct,
    )
    mock_products_qs.get_product.assert_called_once_with(project_id="proj-123", product_id="prod-123")
