import logging
from unittest import mock

import pytest

from app.provisioning.domain.model import (
    additional_configuration,
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
    provisioned_products_query_service,
    system_command_service,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate

PRODUCT_INSTANCE_TYPES = [
    provisioned_product.ProvisionedProductType.VirtualTarget,
    provisioned_product.ProvisionedProductType.Workbench,
]

PRODUCT_CONTAINER_TYPES = [provisioned_product.ProvisionedProductType.Container]


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
def mock_unit_of_work(mock_provisioned_product_repo):
    repo_dict = {
        provisioned_product.ProvisionedProduct: mock_provisioned_product_repo,
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
def get_provisioned_product():
    def _inner(
        status: product_status.ProductStatus = product_status.ProductStatus.Provisioning,
        sc_provisioned_product_id: str | None = None,
        product_id: str = "prod-123",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        provisioned_product_type: provisioned_product.ProvisionedProductType = provisioned_product.ProvisionedProductType.VirtualTarget,
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
        private_ip: str | None = "192.168.1.1",
        ssh_key_path: str | None = None,
        provisioning_parameters: list[provisioning_parameter.ProvisioningParameter] = [
            provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
            provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId", isTechnicalParameter=True),
        ],
        experimental: bool | None = None,
        additional_configurations: list[additional_configuration.AdditionalConfiguration] = [
            additional_configuration.AdditionalConfiguration(
                type=additional_configuration.ProvisionedProductConfigurationTypeEnum.VVPLProvisionedProductConfiguration,
                parameters=[
                    additional_configuration.AdditionalConfigurationParameter(key="param-1", value="value-1"),
                    additional_configuration.AdditionalConfigurationParameter(key="param-2", value="value-2"),
                ],
            )
        ],
    ):
        return provisioned_product.ProvisionedProduct(
            projectId="proj-123",
            provisionedProductId=provisioned_product_id,
            provisionedProductName="my name",
            provisionedProductType=provisioned_product_type,
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
            amiId=("ami-123" if provisioned_product_type in PRODUCT_INSTANCE_TYPES else None),
            containerName=("cont123" if provisioned_product_type in PRODUCT_CONTAINER_TYPES else None),
            containerServiceName=("serv123" if provisioned_product_type in PRODUCT_CONTAINER_TYPES else None),
            containerTaskArn=(
                "arn:aws:ecs:us-east-1:001234567890:task/fargate/ccde2bf0d35b47439e556ded93425144"
                if provisioned_product_type in PRODUCT_CONTAINER_TYPES
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
            sshKeyPath=ssh_key_path,
            experimental=experimental,
            additionalConfigurations=additional_configurations,
        )

    return _inner


@pytest.fixture()
def mock_provisioned_products_qs(get_provisioned_product):
    vt_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    vt_qs.get_by_id.return_value = get_provisioned_product()
    vt_qs.get_provisioned_products_by_user_id.return_value = []
    return vt_qs


@pytest.fixture()
def mock_system_command_service():
    sys_cmd_srv_mock = mock.create_autospec(spec=system_command_service.SystemCommandService)
    sys_cmd_srv_mock.run_document.return_value = "doc-123"
    sys_cmd_srv_mock.get_run_status.return_value = (
        additional_configuration.AdditionalConfigurationRunStatus.Success,
        "Success",
    )
    sys_cmd_srv_mock.is_instance_ready.return_value = True
    return sys_cmd_srv_mock


@pytest.fixture
def mock_instance_mgmt_service():
    instance_mgmt_srv = mock.create_autospec(spec=instance_management_service.InstanceManagementService)
    instance_mgmt_srv.get_instance_state.return_value = product_status.EC2InstanceState.Running
    instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails(
        State=instance_details.InstanceState(Name=product_status.EC2InstanceState.Running),
    )
    return instance_mgmt_srv


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
