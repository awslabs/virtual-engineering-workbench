import logging
from unittest import mock

import pytest
from attr import dataclass

from app.publishing.domain.commands import products_versions_sync_command
from app.publishing.entrypoints.product_sync_event_handler import bootstrapper
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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ProductsVersionSyncEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DOMAIN_EVENT_BUS_ARN", "arn:aws:events:us-east-1:001234567890:event-bus/projects-events")
    monkeypatch.setenv("BOUNDED_CONTEXT", "Publishing")


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
def product_version_sync_requested():
    return {
        "jobName": "ProductsVersionsSyncRequested",
    }


@pytest.fixture()
def mock_product_version_sync_command_handler():
    return mock.Mock()


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def mock_dependencies(
    mock_product_version_sync_command_handler,
    mock_logger,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        ).register_handler(
            products_versions_sync_command.ProductsVersionsSyncCommand, mock_product_version_sync_command_handler
        )
    )
