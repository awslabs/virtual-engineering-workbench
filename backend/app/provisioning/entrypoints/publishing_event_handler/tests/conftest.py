import logging
from unittest import mock

import pytest
from attr import dataclass

from app.provisioning.domain.commands.product_provisioning import (
    check_if_upgrade_available_command,
)
from app.provisioning.domain.read_models import product
from app.provisioning.entrypoints.publishing_event_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus

TEST_TABLE_NAME = "TEST"


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.provisioning.entrypoints.publishing_event_handler.bootstrapper.migrations_config",
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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ProvisioningEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "DOMAIN_EVENT_BUS_ARN",
        "arn:aws:events:us-east-1:001234567890:event-bus/provisioning-events",
    )
    monkeypatch.setenv("BOUNDED_CONTEXT", "Provisioning")


@pytest.fixture
def generate_event():
    def _generate_event(detail_type: str, detail: dict):
        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": detail_type,
            "source": "org.workbench.publishing.dev",
            "account": "123456789012",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": [],
            "detail": detail,
        }

    return _generate_event


@pytest.fixture
def product_availability_updated_event_payload():
    product_availability_dict = {
        "projectId": "proj-12345",
        "productId": "prod-12345",
        "productType": product.ProductType.Workbench,
        "productName": "mock-name",
        "productDescription": "mock description",
        "technologyId": "tech-12345",
        "technologyName": "Technology 1",
        "availableStages": [
            product.ProductStage.DEV,
            product.ProductStage.QA,
            product.ProductStage.PROD,
        ],
        "availableRegions": ["us-east-1", "eu-west-1"],
        "pausedStages": [],
        "pausedRegions": [],
        "lastUpdateDate": "mock-time",
    }
    return product_availability_dict


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def mock_update_product_read_model_event_handler():
    return mock.Mock()


@pytest.fixture
def mock_update_recommended_version_read_model_event_handler():
    return mock.Mock()


@pytest.fixture
def mock_check_upgrade_command_handler():
    return mock.Mock()


@pytest.fixture
def product_version_published_payload():
    return {
        "eventName": "ProductVersionPublished",
        "projectId": "proj-123",
        "productId": "prod-123",
        "versionId": "vers-123",
        "awsAccountId": "123456789012",
        "stage": "DEV",
        "region": "us-east-1",
        "versionName": "3.9.1-rc.3",
        "scProductId": "prod-12345",
        "scProvisioningArtifactId": "pa-12345",
    }


@pytest.fixture
def recommended_version_set_payload():
    return {
        "eventName": "RecommendedVersionSet",
        "projectId": "proj-123",
        "productId": "prod-123",
        "version_id": "vers-2",
    }


@pytest.fixture
def mock_dependencies(
    mock_update_product_read_model_event_handler,
    mock_update_recommended_version_read_model_event_handler,
    mock_logger,
    mock_check_upgrade_command_handler,
):
    return bootstrapper.Dependencies(
        update_product_read_model_event_handler=mock_update_product_read_model_event_handler,
        update_recommended_version_read_model_event_handler=mock_update_recommended_version_read_model_event_handler,
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        ).register_handler(
            check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand,
            mock_check_upgrade_command_handler,
        ),
    )
