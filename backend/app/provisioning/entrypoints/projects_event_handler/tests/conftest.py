import logging
from unittest import mock

import pytest
from attr import dataclass

from app.provisioning.domain.commands.product_provisioning import remove_provisioned_product_command
from app.provisioning.domain.commands.user_profile import cleanup_user_profile_command
from app.provisioning.domain.model import product_status, provisioned_product, provisioning_parameter
from app.provisioning.domain.query_services import provisioned_products_domain_query_service
from app.provisioning.entrypoints.projects_event_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus

TEST_TABLE_NAME = "TEST"


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.provisioning.entrypoints.projects_event_handler.bootstrapper.migrations_config", return_value=[]
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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ProjectsEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DOMAIN_EVENT_BUS_ARN", "arn:aws:events:us-east-1:001234567890:event-bus/projects-events")
    monkeypatch.setenv("BOUNDED_CONTEXT", "products")
    monkeypatch.setenv("PROJECTS_API_URL", "projects-api-url")


@pytest.fixture
def generate_event():
    def _generate_event(detail_type: str, detail: dict):
        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": detail_type,
            "source": "org.workbench.provisioning.dev",
            "account": "123456789012",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": [],
            "detail": detail,
        }

    return _generate_event


@pytest.fixture
def user_unassigned_event():
    return {"eventName": "UserUnAssigned", "userId": "T0011AA", "projectId": "proj-123"}


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def mock_remove_provisioned_product_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_clean_up_user_profile_command_handler():
    return mock.Mock()


@pytest.fixture()
def get_sample_provisioned_product():
    def _inner(
        provisioned_product_id: str = "pp-123",
        status: product_status.ProductStatus = product_status.ProductStatus.Provisioning,
        sc_provisioned_product_id: str | None = None,
        user_id: str = "T0011AA",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        product_id: str = "prod-123",
        provisioned_product_type: provisioned_product.ProvisionedProductType = provisioned_product.ProvisionedProductType.VirtualTarget,
    ):
        return provisioned_product.ProvisionedProduct(
            projectId="proj-123",
            provisionedProductId=provisioned_product_id,
            provisionedProductName="my name",
            provisionedProductType=provisioned_product_type,
            userId=user_id,
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
            stage=stage,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value")
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )

    return _inner


@pytest.fixture
def mock_provisioned_products_domain_query_service(get_sample_provisioned_product):
    mock_qs = mock.create_autospec(spec=provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService)
    mock_qs.get_provisioned_products.return_value = [
        get_sample_provisioned_product(),
        get_sample_provisioned_product(provisioned_product_id="pp-234", status=product_status.ProductStatus.Running),
        get_sample_provisioned_product(provisioned_product_id="pp-345", status=product_status.ProductStatus.Stopped),
    ]
    return mock_qs


@pytest.fixture
def mock_dependencies(
    mock_remove_provisioned_product_command_handler,
    mock_clean_up_user_profile_command_handler,
    mock_provisioned_products_domain_query_service,
    mock_logger,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            remove_provisioned_product_command.RemoveProvisionedProductCommand,
            mock_remove_provisioned_product_command_handler,
        )
        .register_handler(
            cleanup_user_profile_command.CleanUpUserProfileCommand,
            mock_clean_up_user_profile_command_handler,
        ),
        provisioned_products_domain_qry_srv=mock_provisioned_products_domain_query_service,
    )
