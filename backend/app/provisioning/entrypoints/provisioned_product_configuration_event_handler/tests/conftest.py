import json
import logging
from unittest import mock

import boto3
import pytest
from attr import dataclass
from moto import mock_aws

from app.provisioning.domain.commands.provisioned_product_configuration import (
    complete_provisioned_product_configuration_command,
    fail_provisioned_product_configuration_command,
    start_provisioned_product_configuration_command,
)
from app.provisioning.domain.model import additional_configuration
from app.provisioning.domain.query_services import provisioned_product_configuration_domain_query_service
from app.provisioning.entrypoints.provisioned_product_configuration_event_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus

TEST_TABLE_NAME = "TEST"
PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING_PARAM_NAME = (
    "/workbench-provisioning-shared-dev/provisioned-product-configuration-document-mapping"
)
PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING_PARAM_VALUE = {
    "VVPL_PROVISIONED_PRODUCT_CONFIGURATION": "VVPLProvisionedProductDocument"
}


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.provisioning.entrypoints.provisioned_product_configuration_event_handler.bootstrapper.migrations_config",
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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Provisioning")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DOMAIN_EVENT_BUS_ARN", "arn:aws:events:us-east-1:001234567890:event-bus/projects-events")
    monkeypatch.setenv("BOUNDED_CONTEXT", "provisioning")
    monkeypatch.setenv(
        "PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING_PARAM_NAME",
        PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING_PARAM_NAME,
    )


@pytest.fixture(autouse=True)
def ssm_mock():
    with mock_aws():
        yield boto3.client(
            "ssm",
            region_name="us-east-1",
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture(autouse=True)
def mock_provisioned_product_configuration_document_mapping_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name=PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING_PARAM_NAME,
        Value=json.dumps(PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING_PARAM_VALUE),
        Type="String",
    )


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def mock_start_provisioned_product_configuration_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_fail_provisioned_product_configuration_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_complete_provisioned_product_configuration_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_provisioned_product_configuration_domain_qs():
    mock_qs = mock.create_autospec(
        spec=provisioned_product_configuration_domain_query_service.ProvisionedProductConfigurationDomainQueryService,
        instance=True,
    )
    mock_qs.get_provisioned_product_configuration_run_status.return_value = (
        additional_configuration.AdditionalConfigurationRunStatus.Success,
        "Success",
    )
    mock_qs.is_provisioned_product_ready.return_value = True
    return mock_qs


@pytest.fixture
def mock_dependencies(
    mock_logger,
    mock_start_provisioned_product_configuration_command_handler,
    mock_fail_provisioned_product_configuration_command_handler,
    mock_complete_provisioned_product_configuration_command_handler,
    mock_provisioned_product_configuration_domain_qs,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            start_provisioned_product_configuration_command.StartProvisionedProductConfigurationCommand,
            mock_start_provisioned_product_configuration_command_handler,
        )
        .register_handler(
            fail_provisioned_product_configuration_command.FailProvisionedProductConfigurationCommand,
            mock_fail_provisioned_product_configuration_command_handler,
        )
        .register_handler(
            complete_provisioned_product_configuration_command.CompleteProvisionedProductConfigurationCommand,
            mock_complete_provisioned_product_configuration_command_handler,
        ),
        provisioned_product_configuration_domain_qs=mock_provisioned_product_configuration_domain_qs,
    )
