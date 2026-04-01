import logging
from unittest import mock

import pytest

from app.provisioning.domain.model import (
    additional_configuration,
    block_device_mappings,
    container_details,
    instance_details,
    maintenance_window,
    product_status,
    provisioned_product,
    provisioned_product_details,
    provisioned_product_output,
    provisioning_parameter,
    user_profile,
)
from app.provisioning.domain.ports import (
    container_management_service,
    instance_management_service,
    parameter_service,
    products_query_service,
    products_service,
    projects_query_service,
    provisioned_products_query_service,
    publishing_query_service,
    system_command_service,
)
from app.provisioning.domain.read_models import (
    component_version_detail,
    product,
    project_assignment,
    version,
)
from app.shared.adapters.feature_toggling import backend_feature_toggles
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate

TEST_OS_VERSION = "Ubuntu 24"
TEST_COMPONENT_VERSION_DETAILS = [
    component_version_detail.ComponentVersionDetail(
        componentName="VS Code",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
        softwareVendor="Microsoft",
        softwareVersion="1.87.0",
    )
]
TEST_COMPONENT_VERSION_DETAILS_DUMPED = [cvd.model_dump() for cvd in TEST_COMPONENT_VERSION_DETAILS]


@pytest.fixture()
def publishing_qry_svc_mock():
    qry_svc = mock.create_autospec(spec=publishing_query_service.PublishingQueryService)
    return qry_svc


@pytest.fixture()
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture()
def mock_message_bus():
    return mock.create_autospec(spec=message_bus.MessageBus)


@pytest.fixture()
def mock_provisioned_product_repo():
    return mock.create_autospec(spec=unit_of_work.GenericRepository)


@pytest.fixture()
def mock_user_profile_repo(get_test_user_profile):
    user_profile_repo = mock.create_autospec(spec=unit_of_work.GenericRepository)
    user_profile_repo.get.return_value = get_test_user_profile()
    return user_profile_repo


@pytest.fixture()
def mock_products_repo():
    repo = mock.create_autospec(spec=unit_of_work.GenericRepository)
    return repo


@pytest.fixture()
def mock_unit_of_work(mock_provisioned_product_repo, mock_user_profile_repo, mock_products_repo):
    repo_dict = {
        provisioned_product.ProvisionedProduct: mock_provisioned_product_repo,
        user_profile.UserProfile: mock_user_profile_repo,
        product.Product: mock_products_repo,
    }

    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork)
    uow_mock.get_repository.side_effect = lambda pk_param, entity_param: repo_dict.get(entity_param)
    return uow_mock


@pytest.fixture()
def mock_publisher(mock_message_bus, mock_unit_of_work):
    return aggregate.AggregatePublisher(
        mb=mock_message_bus,
        uow=mock_unit_of_work,
    )


@pytest.fixture()
def mock_be_feature_toggles_srv():
    mock_ft = mock.create_autospec(spec=backend_feature_toggles.BackendFeatureToggles)
    mock_ft.is_enabled.return_value = True
    return mock_ft


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
        recommendation_reason: str = None,
        recommended_instance_type: str = None,
        last_update_by: str = "T0011AA",
        created_by: str = "T0011AA",
        old_instance_id: str | None = None,
        deployment_option: str | None = None,
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
            amiId=("ami-123" if provision_product_type in provisioned_product.PRODUCT_INSTANCE_TYPES else None),
            containerClusterName=(
                "clust123" if provision_product_type in provisioned_product.PRODUCT_CONTAINER_TYPES else None
            ),
            containerName=(
                "cont123" if provision_product_type in provisioned_product.PRODUCT_CONTAINER_TYPES else None
            ),
            containerServiceName=(
                "serv123" if provision_product_type in provisioned_product.PRODUCT_CONTAINER_TYPES else None
            ),
            containerTaskArn=(
                "arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144"
                if provision_product_type in provisioned_product.PRODUCT_CONTAINER_TYPES
                else None
            ),
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=provisioning_parameters,
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate=last_update_date,
            createdBy=created_by,
            lastUpdatedBy=last_update_by,
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
            instanceRecommendationReason=(recommendation_reason if recommendation_reason else None),
            recommendedInstanceType=(recommended_instance_type if recommended_instance_type else None),
            oldInstanceId=old_instance_id,
            deploymentOption=deployment_option,
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
        version_name: str = "1.0.0",
        last_updated_date: str = "2000-01-01",
        is_recommended_version: bool = True,
        parameters: list[version.VersionParameter] | None = None,
        sc_provisioning_artifact_id: str = "sc-vers-123",
        is_container: bool = False,
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
            amiId="ami-123" if not is_container else None,
            scProductId="sc-prod-123",
            scProvisioningArtifactId=sc_provisioning_artifact_id,
            isRecommendedVersion=is_recommended_version,
            lastUpdateDate=last_updated_date,
            parameters=parameters,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
        )

    return _get_test_version


@pytest.fixture
def get_test_block_device_mappings():
    def _inner():
        return block_device_mappings.BlockDeviceMappings(
            rootDeviceName="/dev/sda1",
            mappings=[
                block_device_mappings.BlockDevice(deviceName="/dev/sda1", volumeId="vol-1234567890"),
                block_device_mappings.BlockDevice(deviceName="/dev/sdb", volumeId="vol-0987654321"),
            ],
        )

    return _inner


@pytest.fixture
def get_test_product():
    def _get_test_product(
        product_id: str = "prod-123",
        last_update_date: str = "2023-12-05T00:00:00+00:00",
        average_provisioning_time: int = None,
        total_reported_times: int = None,
        product_type: product.ProductType = product.ProductType.VirtualTarget,
    ):
        return product.Product(
            projectId="proj-123",
            productId=product_id,
            technologyId="t-123",
            technologyName="test tech",
            productName="Pied Piper",
            productType=product_type,
            lastUpdateDate=last_update_date,
            averageProvisioningTime=average_provisioning_time,
            totalReportedTimes=total_reported_times,
        )

    return _get_test_product


@pytest.fixture()
def get_test_user_profile():
    def _inner(
        user_id: str = "T0011AA",
        preferred_region: str = "us-east-1",
    ):
        return user_profile.UserProfile(
            userId=user_id,
            preferredRegion=preferred_region,
            preferredNetwork="x",
            preferredMaintenanceWindows=[
                maintenance_window.MaintenanceWindow(
                    day=maintenance_window.WeekDay.MONDAY,
                    startTime="00:00",
                    endTime="04:00",
                    userId=user_id,
                )
            ],
            createDate="2024-01-18T00:00:00+00:00",
            lastUpdateDate="2024-01-18T00:00:00+00:00",
        )

    return _inner


@pytest.fixture()
def mock_provisioned_products_qs(get_provisioned_product):
    vt_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    vt_qs.get_by_id.return_value = get_provisioned_product()
    vt_qs.get_provisioned_products_by_user_id.return_value = []
    return vt_qs


@pytest.fixture()
def mock_products_qs():
    qs = mock.create_autospec(spec=products_query_service.ProductsQueryService)
    return qs


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
        provisioned_product_output.ProvisionedProductOutput(
            outputKey="SSHKeyPair",
            outputValue="/ec2/keypair/i-123",
            description="SSM Parameter containing the ssh key generated",
        ),
    ]
    products_srv.get_provisioned_product_details.return_value = provisioned_product_details.ProvisionedProductDetails(
        Tags=[],
        Status=product_status.ServiceCatalogStatus.Available,
        Id="pp-123",
        ProvisioningArtifactId="pa-321",
    )
    products_srv.has_provisioned_product_insufficient_capacity_error.return_value = False
    products_srv.has_provisioned_product_missing_removal_signal_error.return_value = False
    return products_srv


@pytest.fixture
def mock_parameter_srv():
    parameter_srv = mock.create_autospec(spec=parameter_service.ParameterService)
    parameter_srv.get_parameter_value.return_value = "vpc-12345"
    return parameter_srv


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


@pytest.fixture
def mock_instance_mgmt_srv(
    get_test_block_device_mappings,
    mock_public_route_table,
    mock_private_route_table,
    mock_subnet,
):
    instance_mgmt_srv = mock.create_autospec(spec=instance_management_service.InstanceManagementService)
    instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Stopped
    instance_mgmt_srv.get_instance_platform.return_value = "Windows"
    instance_mgmt_srv.start_instance.return_value = product_status.EC2InstanceState.Pending
    instance_mgmt_srv.stop_instance.return_value = product_status.EC2InstanceState.Stopping
    instance_mgmt_srv.get_user_security_group_id.return_value = None
    instance_mgmt_srv.create_user_security_group.return_value = "sg-12345"
    instance_mgmt_srv.get_block_device_mappings.return_value = get_test_block_device_mappings()
    instance_mgmt_srv.describe_vpc_route_tables.return_value = [
        mock_public_route_table(),
        mock_private_route_table(),
    ]
    instance_mgmt_srv.describe_vpc_subnets.return_value = [
        mock_subnet(subnet_id="s-pub", available_ip_address_count=120, availability_zone="az-2"),
        mock_subnet(subnet_id="s-prv", available_ip_address_count=100, availability_zone="az-1"),
    ]
    instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Stopped),
        PrivateIpAddress="192.168.1.1",
    )
    return instance_mgmt_srv


@pytest.fixture
def mock_command_srv():
    instance_mgmt_srv = mock.create_autospec(spec=system_command_service.SystemCommandService)
    instance_mgmt_srv.run_command.return_value = "command-id-5"
    return instance_mgmt_srv


@pytest.fixture
def mock_experimental_provisioned_product_per_project_limit():
    return 20


@pytest.fixture
def mocked_projects_qs():
    m = mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
    m.get_project_assignment.return_value = project_assignment.ProjectAssignment(
        userId="test-user", roles=["PLATFORM_USER"]
    )
    return mock.create_autospec(spec=projects_query_service.ProjectsQueryService)
