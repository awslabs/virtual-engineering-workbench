import logging
from unittest import mock

import pytest
from attr import dataclass

from app.publishing.entrypoints.packaging_event_handler import bootstrapper
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
    monkeypatch.setenv("TABLE_NAME", TEST_TABLE_NAME)
    monkeypatch.setenv("GSI_NAME_ENTITIES", "gsi_entities")
    monkeypatch.setenv("ADMIN_ROLE", "test-admin-role")
    monkeypatch.setenv("TOOLS_AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("TEMPLATES_S3_BUCKET_NAME", "test-templates-bucket")
    monkeypatch.setenv("WORKBENCH_TEMPLATE_FILE_PATH", "templates/workbench-template.yml")
    monkeypatch.setenv("VIRTUAL_TARGET_TEMPLATE_FILE_PATH", "templates/virtual-target-template.yml")
    monkeypatch.setenv("CONTAINER_TEMPLATE_NAME_FILE_PATH", "templates/container-template.yml")
    monkeypatch.setenv("PRODUCT_VERSION_LIMIT_PARAM_NAME", "/test/product-limit-version")
    monkeypatch.setenv("PRODUCT_RC_VERSION_LIMIT_PARAM_NAME", "/test/product-limit-rc-version")


@pytest.fixture
def generate_event():
    def _generate_event(detail_type: str, detail: dict):
        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": detail_type,
            "source": "org.workbench.packaging.dev",
            "account": "123456789012",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": [],
            "detail": detail,
        }

    return _generate_event


@pytest.fixture
def image_registration_completed_event_payload():
    return {
        "eventName": "ImageRegistrationCompleted",
        "projectId": "proj-12345",
        "amiDescription": "srujande-linux-test-recipe",
        "amiId": "ami-0583ab768d71fb824",
        "amiName": "Version 2.0.0 of srujande-linux-test-recipe",
        "componentsVersionsDetails": [
            {
                "componentName": "srujande-linux-test",
                "componentVersionType": "MAIN",
                "softwareVendor": "srujande-linux",
                "softwareVersion": "1.0.0",
                "licenseDashboard": "some license dashboard",
                "notes": "This is a test note",
            }
        ],
        "retiredAmiIds": ["ami-07ed33791d87e939f"],
        "osVersion": "Ubuntu 24",
        "platform": "Linux",
        "architecture": "amd64",
        "integrations": ["GitHub"],
        "createDate": "2024-02-29T14:15:39.412367+00:00",
    }


@pytest.fixture
def image_deregistered_event_payload():
    return {
        "eventName": "ImageDeregistered",
        "amiId": "ami-0583ab768d71fb824",
    }


@pytest.fixture
def automated_image_registration_completed_event_payload():
    return {
        "eventName": "AutomatedImageRegistrationCompleted",
        "amiId": "ami-12345678",
        "productId": "product-123",
        "projectId": "project-456",
        "releaseType": "MINOR",
        "userId": "T123456",
        "componentsVersionsDetails": [
            {
                "componentName": "test-component",
                "componentVersionType": "MAIN",
                "softwareVendor": "test-vendor",
                "softwareVersion": "1.0.0",
                "licenseDashboard": None,
                "notes": None,
            }
        ],
        "osVersion": "Ubuntu 24",
        "platform": "Linux",
        "architecture": "amd64",
        "integrations": ["GitHub"],
    }


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture()
def mock_update_ami_read_model_event_handler():
    yield mock.Mock()


@pytest.fixture()
def mock_delete_ami_read_model_event_handler():
    yield mock.Mock()


@pytest.fixture()
def mock_create_automated_version_event_handler():
    yield mock.Mock()


@pytest.fixture
def mock_dependencies(
    mock_logger,
    mock_update_ami_read_model_event_handler,
    mock_delete_ami_read_model_event_handler,
    mock_create_automated_version_event_handler,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        ),
        update_ami_read_model_event_handler=mock_update_ami_read_model_event_handler,
        delete_ami_read_model_event_handler=mock_delete_ami_read_model_event_handler,
        create_automated_version_event_handler=mock_create_automated_version_event_handler,
    )
