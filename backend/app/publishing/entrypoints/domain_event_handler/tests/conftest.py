import logging
from unittest import mock

import pytest
from attr import dataclass

from app.publishing.domain.commands import (
    publish_version_command,
    rename_version_distributions_command,
    unpublish_product_command,
    unpublish_version_command,
    update_product_availability_command,
)
from app.publishing.domain.model import product
from app.publishing.entrypoints.domain_event_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus

TEST_TABLE_NAME = "TEST"


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
    monkeypatch.setenv(
        "DOMAIN_EVENT_BUS_ARN",
        "arn:aws:events:us-east-1:001234567890:event-bus/projects-events",
    )
    monkeypatch.setenv("BOUNDED_CONTEXT", "Publishing")
    monkeypatch.setenv("ADMIN_ROLE", "Admin")
    monkeypatch.setenv("USE_CASE_ROLE", "UseCase")
    monkeypatch.setenv("LAUNCH_CONSTRAINT_ROLE", "LaunchConstraint")
    monkeypatch.setenv("TOOLS_AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("WORKBENCH_TEMPLATE_FILE_PATH", "templates/workbench-template.yml")


@pytest.fixture
def generate_event():
    def _generate_event(detail_type: str, detail: dict):
        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": detail_type,
            "source": "org.workbench.projects.dev",
            "account": "123456789012",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": [],
            "detail": detail,
        }

    return _generate_event


@pytest.fixture()
def product_version_name_updated_event_payload():
    return {
        "productId": "prod-123",
        "versionId": "vers-123",
        "awsAccountId": "123456789012",
    }


@pytest.fixture()
def product_version_retire_started_event_payload():
    return {
        "productId": "prod-123",
        "versionId": "vers-123",
        "awsAccountId": "123456789012",
        "region": "us-east-1",
    }


@pytest.fixture
def product_version_ami_shared_event_payload():
    return {
        "productId": "prod-123",
        "versionId": "vers-123",
        "awsAccountId": "123456789012",
        "previousEventName": "ProductVersionCreationStarted",
    }


@pytest.fixture
def product_archiving_started_event_payload():
    return {
        "eventName": "ProductArchivingStarted",
        "projectId": "proj-123",
        "productId": "prod-123",
    }


@pytest.fixture
def product_version_published_event_payload():
    return {
        "eventName": "ProductVersionPublished",
        "projectId": "proj-123",
        "productId": "prod-123",
        "versionId": "vers-123",
        "awsAccountId": "123456789012",
        "stage": "DEV",
        "versionName": "3.9.1-rc.3",
        "scProductId": "prod-12345",
        "scProvisioningArtifactId": "pa-12345",
        "amiId": "ami-12345",
    }


@pytest.fixture
def product_version_unpublished_event_payload():
    return {
        "eventName": "ProductVersionUnpublished",
        "projectId": "proj-123",
        "productId": "prod-123",
        "versionId": "vers-123",
        "awsAccountId": "123456789012",
    }


@pytest.fixture
def product_unpublished_event_payload():
    return {
        "eventName": "ProductUnpublished",
        "projectId": "proj-123",
        "productId": "prod-123",
    }


@pytest.fixture
def product_availability_updated_event_payload():
    return {
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


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def mock_publish_version_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_rename_version_distributions_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_unpublish_product_command_handler():
    return mock.Mock()


@pytest.fixture()
def mock_unpublish_version_command_handler():
    return mock.Mock()


@pytest.fixture()
def mock_update_product_availability_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_dependencies(
    mock_publish_version_command_handler,
    mock_rename_version_distributions_command_handler,
    mock_unpublish_product_command_handler,
    mock_unpublish_version_command_handler,
    mock_update_product_availability_command_handler,
    mock_logger,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            publish_version_command.PublishVersionCommand,
            mock_publish_version_command_handler,
        )
        .register_handler(
            rename_version_distributions_command.RenameVersionDistributionsCommand,
            mock_rename_version_distributions_command_handler,
        )
        .register_handler(
            unpublish_product_command.UnpublishProductCommand,
            mock_unpublish_product_command_handler,
        )
        .register_handler(
            unpublish_version_command.UnpublishVersionCommand,
            mock_unpublish_version_command_handler,
        )
        .register_handler(
            update_product_availability_command.UpdateProductAvailabilityCommand,
            mock_update_product_availability_command_handler,
        )
    )
