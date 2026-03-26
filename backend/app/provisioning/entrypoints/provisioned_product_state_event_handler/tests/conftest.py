import logging
from unittest import mock

import pytest
from attr import dataclass

from app.provisioning.adapters.services import ec2_instance_management_service, ecs_container_management_service
from app.provisioning.domain.commands.product_provisioning import update_provisioned_product_command
from app.provisioning.domain.commands.provisioned_product_state import (
    complete_provisioned_product_start_command,
    complete_provisioned_product_stop_command,
)
from app.provisioning.domain.model import (
    container_details,
    instance_details,
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.ports import provisioned_products_query_service
from app.provisioning.entrypoints.provisioned_product_state_event_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus

TEST_TABLE_NAME = "TEST"


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.provisioning.entrypoints.provisioned_product_state_event_handler.bootstrapper.migrations_config",
        return_value=[],
    ):
        yield


@pytest.fixture
def lambda_context():
    @dataclass
    class context:
        function_name = "test"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:eu-west-1:000000000:function:test"
        aws_request_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    return context


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT", "123456789012")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "VirtualTargetEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DOMAIN_EVENT_BUS_ARN", "arn:aws:events:us-east-1:001234567890:event-bus/virtual-target-events")
    monkeypatch.setenv("BOUNDED_CONTEXT", "Provisioning")
    monkeypatch.setenv("SPOKE_ACCOUNT_VPC_ID_PARAM_NAME", "/workbench/vpc/vpc-id")
    monkeypatch.setenv("PROVISIONING_SUBNET_SELECTOR", "PrivateSubnetWithTransitGateway")


@pytest.fixture
def generate_event():
    def _generate_event(
        status: str,
    ):
        return {
            "version": "0",
            "id": "7bf73129-1428-4cd3-a780-95db273d1602",
            "detail-type": "WorkbenchEC2StateChanged",
            "source": "proserve.workbench.catalogservice.dev",
            "account": "123456789012",
            "time": "2024-01-12T13:44:30Z",
            "region": "us-east-1",
            "resources": ["i-abcd1111"],
            "detail": {"instanceId": "i-abcd1111", "state": status, "accountId": "123456789013", "region": "us-east-1"},
        }

    return _generate_event


@pytest.fixture()
def generate_ecs_task_state_change_event():
    def _generate_ecs_task_state_change_event(last_status: str = "running"):
        return {
            "version": "0",
            "id": "7bf73129-1428-4cd3-a780-95db273d1602",
            "detail-type": "WorkbenchContainerStateChanged",
            "source": "aws.ecs",
            "account": "123456789012",
            "time": "2024-01-12T13:44:30Z",
            "region": "us-east-1",
            "detail": {
                "attachments": [
                    {
                        "id": "1789bcae-ddfb-4d10-8ebe-8ac87ddba5b8",
                        "type": "eni",
                        "status": "ATTACHED",
                        "details": [
                            {"name": "subnetId", "value": "subnet-abcd1234"},
                            {"name": "networkInterfaceId", "value": "eni-abcd1234"},
                            {"name": "macAddress", "value": "0a:98:eb:a7:29:ba"},
                            {"name": "privateIPv4Address", "value": "10.0.0.139"},
                        ],
                    }
                ],
                "taskArn": "arn:aws:ecs:us-west-2:111122223333:task/FargateCluster/c13b4cb40f1f4fe4a2971f76ae5a47ad",
                "clusterArn": "arn:aws:ecs:us-west-2:111122223333:cluster/clust123",
                "lastStatus": last_status.upper(),
                "accountId": "123456789013",
                "region": "us-east-1",
            },
        }

    return _generate_ecs_task_state_change_event


@pytest.fixture
def mock_instance_mgmt_srv():
    instance_mgmt_srv = mock.create_autospec(spec=ec2_instance_management_service.EC2InstanceManagementService)
    instance_mgmt_srv.get_instance_details.return_value = instance_details.InstanceDetails.parse_obj(
        {
            "State": {"Name": "running"},
            "Tags": [
                {"Key": "Name", "ResourceId": "i-abcd1111", "ResourceType": "instance", "Value": "instanceName"},
                {"Key": "Environment", "ResourceId": "i-abcd1111", "ResourceType": "instance", "Value": "DEV"},
                {
                    "Key": "vew:provisionedProduct:productType",
                    "ResourceId": "i-abcd1111",
                    "ResourceType": "instance",
                    "Value": "VIRTUAL_TARGET",
                },
                {
                    "Key": "vew:provisionedProduct:id",
                    "ResourceId": "i-abcd1111",
                    "ResourceType": "instance",
                    "Value": "vt-12345",
                },
                {
                    "Key": "aws:servicecatalog:provisionedProductArn",
                    "ResourceId": "i-abcd1111",
                    "ResourceType": "instance",
                    "Value": "arn:aws:servicecatalog:us-east-1:001234567890:stack/prod/pp-12345",
                },
            ],
        }
    )
    return instance_mgmt_srv


@pytest.fixture
def mock_container_mgmt_srv():
    container_mgmt_srv = mock.create_autospec(spec=ecs_container_management_service.ECSContainerManagementService)
    container_mgmt_srv.get_container_tags_from_task_arn.return_value = [
        container_details.ContainerTag.parse_obj({"Key": "Name", "Value": "taskArn"}),
        container_details.ContainerTag.parse_obj({"Key": "Environment", "Value": "DEV"}),
        container_details.ContainerTag.parse_obj(
            {
                "Key": "vew:provisionedProduct:productType",
                "Value": "Container",
            }
        ),
        container_details.ContainerTag.parse_obj(
            {
                "Key": "vew:provisionedProduct:id",
                "Value": "vt-12345",
            }
        ),
        container_details.ContainerTag.parse_obj(
            {
                "Key": "aws:servicecatalog:provisionedProductArn",
                "Value": "arn:aws:servicecatalog:us-east-1:001234567890:stack/prod/pp-12345",
            }
        ),
    ]
    return container_mgmt_srv


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def complete_provisioned_product_start_command_handler():
    return mock.Mock()


@pytest.fixture
def complete_provisioned_product_stop_command_handler():
    return mock.Mock()


@pytest.fixture
def update_provisioned_product_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_dependencies(
    complete_provisioned_product_start_command_handler,
    complete_provisioned_product_stop_command_handler,
    update_provisioned_product_command_handler,
    mock_instance_mgmt_srv,
    mock_container_mgmt_srv,
    mock_logger,
    mock_pp_qs,
):
    return bootstrapper.Dependencies(
        instance_mgmt_srv=mock_instance_mgmt_srv,
        container_mgmt_srv=mock_container_mgmt_srv,
        provisioned_products_query_service=mock_pp_qs,
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            complete_provisioned_product_start_command.CompleteProvisionedProductStartCommand,
            complete_provisioned_product_start_command_handler,
        )
        .register_handler(
            complete_provisioned_product_stop_command.CompleteProvisionedProductStopCommand,
            complete_provisioned_product_stop_command_handler,
        )
        .register_handler(
            update_provisioned_product_command.UpdateProvisionedProductCommand,
            update_provisioned_product_command_handler,
        ),
    )


@pytest.fixture()
def get_provisioned_product():
    def _inner(
        status: product_status.ProductStatus = product_status.ProductStatus.Starting,
        sc_provisioned_product_id: str | None = "pp-12345",
        product_id: str = "prod-123",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        provisioned_product_type: provisioned_product.ProvisionedProductType = provisioned_product.ProvisionedProductType.VirtualTarget,
        region: str = "us-east-1",
        version_id: str = "vers-123",
        provisioned_product_id: str = "pp-123",
        new_version_id: str | None = None,
        new_version_name: str | None = None,
        upgrade_available: bool | None = None,
        version_name: str = "v1.0.0",
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
            instanceId="i-01234567890abcdef",
            stage=stage,
            region=region,
            amiId=(
                "ami-123"
                if provisioned_product_type == provisioned_product.ProvisionedProductType.VirtualTarget
                else None
            ),
            containerName=(
                "cont123" if provisioned_product_type == provisioned_product.ProvisionedProductType.Container else None
            ),
            containerServiceName=(
                "serv123" if provisioned_product_type == provisioned_product.ProvisionedProductType.Container else None
            ),
            containerClusterName=(
                "clust123" if provisioned_product_type == provisioned_product.ProvisionedProductType.Container else None
            ),
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            newVersionId=new_version_id,
            newVersionName=new_version_name,
            upgradeAvailable=upgrade_available,
        )

    return _inner


@pytest.fixture(autouse=True)
def mock_pp_qs(get_provisioned_product):
    vt_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    vt_qs.get_by_sc_provisioned_product_id.return_value = get_provisioned_product()
    return vt_qs
