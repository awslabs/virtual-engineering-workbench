import logging
import typing
from unittest import mock

import pytest

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
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    parameter_service,
    products_service,
    provisioned_products_query_service,
)
from app.provisioning.domain.read_models import version
from app.provisioning.domain.tests.product_provisioning.conftest import (
    TEST_COMPONENT_VERSION_DETAILS,
    TEST_OS_VERSION,
)
from app.shared.adapters.boto.boto_provider import BotoProviderOptions
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate

PRODUCT_INSTANCE_TYPES = [
    provisioned_product.ProvisionedProductType.VirtualTarget,
    provisioned_product.ProvisionedProductType.Workbench,
]

PRODUCT_CONTAINER_TYPES = [provisioned_product.ProvisionedProductType.Container]


@pytest.fixture()
def mock_client_provider():
    return mock.create_autospec(spec=typing.Callable[[BotoProviderOptions], typing.Any])


@pytest.fixture()
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture()
def mock_message_bus():
    return mock.create_autospec(spec=message_bus.MessageBus)


@pytest.fixture()
def mock_virtual_target_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository)


@pytest.fixture()
def mock_unit_of_work(mock_virtual_target_repo):
    repo_dict = {provisioned_product.ProvisionedProduct: mock_virtual_target_repo}

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk_param, entity_param: repo_dict.get(entity_param)
    return uow_mock


@pytest.fixture
def mock_container_mgmt_srv():
    container_mgmt_srv = mock.create_autospec(spec=container_management_service.ContainerManagementService)
    container_mgmt_srv.get_container_details.return_value = container_details.ContainerDetails(
        state=container_details.ContainerState(Name=product_status.TaskState.Running),
        private_ip_address="192.168.1.1",
        task_arn="arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144",
        name="cont123",
    )
    return container_mgmt_srv


@pytest.fixture()
def mock_publisher(mock_message_bus, mock_unit_of_work):
    return aggregate.AggregatePublisher(
        mb=mock_message_bus,
        uow=mock_unit_of_work,
    )


@pytest.fixture()
def get_provisioned_product():
    def _inner(
        status: product_status.ProductStatus = product_status.ProductStatus.Provisioning,
        sc_provisioned_product_id: str | None = None,
        product_id: str = "prod-123",
        provision_product_type: provisioned_product.ProvisionedProductType = provisioned_product.ProvisionedProductType.VirtualTarget,
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        region: str = "us-east-1",
        version_id: str = "vers-123",
        provisioned_product_id: str = "pp-123",
        new_version_id: str | None = None,
        new_version_name: str | None = None,
        upgrade_available: bool | None = None,
        version_name: str = "1.0.0",
        new_provisioning_parameters: list[provisioning_parameter.ProvisioningParameter] | None = None,
        last_update_date: str = "2023-12-05T00:00:00+00:00",
        new_sc_provisioning_artifact_id: str | None = None,
        status_reason: str | None = None,
        outputs: list[provisioned_product_output.ProvisionedProductOutput] | None = None,
        instance_id: str = "i-01234567890abcdef",
        private_ip: str | None = None,
        public_ip: str | None = None,
        ssh_key_path: str | None = None,
        provisioning_parameters: list[provisioning_parameter.ProvisioningParameter] = [
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
        ],
        experimental: bool | None = None,
        additional_configurations: list[additional_configuration.AdditionalConfiguration] | None = None,
        block_device_mappings: block_device_mappings.BlockDeviceMappings | None = None,
        availability_zones_triggered: list[str] | None = None,
        user_ip_address: str | None = None,
        start_date: str | None = None,
    ):
        return provisioned_product.ProvisionedProduct(
            projectId="proj-123",
            provisionedProductId=provisioned_product_id,
            provisionedProductName="my name",
            provisionedProductType=provision_product_type,
            userId="T0011AA",
            userDomains=["domain"],
            status=status,
            productId=product_id,
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId=version_id,
            versionName=version_name,
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId=instance_id,
            stage=stage,
            region=region,
            amiId=("ami-123" if provision_product_type in PRODUCT_INSTANCE_TYPES else None),
            containerClusterName=("clust123" if provision_product_type in PRODUCT_CONTAINER_TYPES else None),
            containerName=("cont123" if provision_product_type in PRODUCT_CONTAINER_TYPES else None),
            containerServiceName=("serv123" if provision_product_type in PRODUCT_CONTAINER_TYPES else None),
            containerTaskArn=(
                "arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144"
                if provision_product_type in PRODUCT_CONTAINER_TYPES
                else None
            ),
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=provisioning_parameters,
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate=last_update_date,
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            newVersionId=new_version_id,
            newVersionName=new_version_name,
            newProvisioningParameters=new_provisioning_parameters,
            newSCProvisioningArtifactId=new_sc_provisioning_artifact_id,
            upgradeAvailable=upgrade_available,
            statusReason=status_reason,
            outputs=outputs,
            privateIp=private_ip,
            publicIp=public_ip,
            sshKeyPath=ssh_key_path,
            experimental=experimental,
            additionalConfigurations=additional_configurations,
            blockDeviceMappings=block_device_mappings,
            availabilityZonesTriggered=availability_zones_triggered,
            userIpAddress=user_ip_address,
            startDate=start_date,
        )

    return _inner


@pytest.fixture()
def get_virtual_target():
    def _inner(
        status: product_status.ProductStatus = product_status.ProductStatus.Provisioning,
        sc_provisioned_product_id: str | None = None,
        product_id: str = "prod-123",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        region: str = "us-east-1",
        create_date: str = "2023-12-05T00:00:00+00:00",
        last_update_date: str = "2023-12-05T00:00:00+00:00",
        instance_id: str | None = "i-01234567890abcdef",
        provisioned_product_id: str = "pp-123",
        start_date: str | None = None,
    ):
        return provisioned_product.ProvisionedProduct(
            projectId="proj-123",
            provisionedProductId=provisioned_product_id,
            provisionedProductName="my name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=status,
            productId=product_id,
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            instanceId=instance_id,
            stage=stage,
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId"),
            ],
            createDate=create_date,
            lastUpdateDate=last_update_date,
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            startDate=start_date,
        )

    return _inner


@pytest.fixture
def get_test_version():
    def _get_test_version(
        product_id: str = "prod-123",
        version_id: str = "vers-123",
        aws_account_id: str = "001234567890",
        stage: version.VersionStage = version.VersionStage.DEV,
        region: str = "us-east-1",
        version_name: str = "v1.0.0",
        last_updated_date: str = "2000-01-01",
        is_recommended_version: bool = True,
    ):
        return version.Version(
            projectId="proj-123",
            productId=product_id,
            technologyId="t-123",
            versionId=version_id,
            versionName=version_name,
            versionDescription="Test Description",
            awsAccountId=aws_account_id,
            stage=stage,
            accountId="account-id-12345",
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-vers-123",
            isRecommendedVersion=is_recommended_version,
            lastUpdateDate=last_updated_date,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
        )

    return _get_test_version


@pytest.fixture()
def mock_virtual_targets_qs(get_virtual_target):
    vt_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    vt_qs.get_by_id.return_value = get_virtual_target()
    vt_qs.get_provisioned_products_by_user_id.return_value = []
    vt_qs.get_all_provisioned_products.return_value = [get_virtual_target()]
    return vt_qs


@pytest.fixture()
def mock_products_srv():
    products_srv = mock.create_autospec(spec=products_service.ProductsService)
    products_srv.provision_product.return_value = "pp-123"
    products_srv.get_provisioned_product_outputs.return_value = [
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="instance-id",
            outputValue="i-1234567890",
            description="description",
        ),
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="privateIp", outputValue="192.168.1.1", description="description"
        ),
    ]
    return products_srv


@pytest.fixture
def mock_parameter_srv():
    parameter_srv = mock.create_autospec(spec=parameter_service.ParameterService)
    parameter_srv.get_parameter_value.return_value = "vpc-12345"
    return parameter_srv


@pytest.fixture
def mock_instance_mgmt_srv():
    instance_mgmt_srv = mock.create_autospec(spec=instance_management_service.InstanceManagementService)
    instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Stopped
    instance_mgmt_srv.start_instance.return_value = product_status.EC2InstanceState.Pending
    instance_mgmt_srv.stop_instance.return_value = product_status.EC2InstanceState.Stopping
    instance_mgmt_srv.get_user_security_group_id.return_value = None
    instance_mgmt_srv.create_user_security_group.return_value = "sg-12345"
    instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Stopped),
        PrivateIpAddress="192.168.1.1",
    )
    return instance_mgmt_srv
