import logging
from unittest import mock

import pytest
from attr import dataclass

from app.publishing.domain.commands import (
    copy_ami_command,
    fail_ami_sharing_command,
    share_ami_command,
    succeed_ami_sharing_command,
)
from app.publishing.domain.query_services import shared_amis_domain_query_service
from app.publishing.entrypoints.ami_sharing import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus


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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "AmiSharing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DOMAIN_EVENT_BUS_ARN", "arn:aws:events:us-east-1:001234567890:event-bus/domain-events")
    monkeypatch.setenv("BOUNDED_CONTEXT", "Publishing")
    monkeypatch.setenv("TABLE_NAME", "TestTable")
    monkeypatch.setenv("IMAGE_SERVICE_ROLE", "TestRole")
    monkeypatch.setenv("IMAGE_SERVICE_AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("IMAGE_SERVICE_KEY_NAME", "test-key")


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def mock_copy_ami_command_handler():
    copy_ami_mock = mock.Mock()
    copy_ami_mock.return_value = "ami-54321"
    return copy_ami_mock


@pytest.fixture
def mock_share_ami_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_succeed_ami_sharing_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_fail_ami_sharing_command_handler():
    return mock.Mock()


@pytest.fixture()
def shared_amis_domain_qry_svc():
    qry_svc = mock.create_autospec(spec=shared_amis_domain_query_service.SharedAMIsDomainQueryService)
    qry_svc.make_share_ami_decision.return_value = (
        shared_amis_domain_query_service.ShareAmiDecision.Done,
        "eu-west-3",
        "ami-12345",
        "ami-54321",
    )
    qry_svc.verify_copy.return_value = True
    return qry_svc


@pytest.fixture
def mock_dependencies(
    mock_logger,
    mock_copy_ami_command_handler,
    mock_share_ami_command_handler,
    mock_succeed_ami_sharing_command_handler,
    mock_fail_ami_sharing_command_handler,
    shared_amis_domain_qry_svc,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(copy_ami_command.CopyAmiCommand, mock_copy_ami_command_handler)
        .register_handler(share_ami_command.ShareAmiCommand, mock_share_ami_command_handler)
        .register_handler(
            succeed_ami_sharing_command.SucceedAmiSharingCommand, mock_succeed_ami_sharing_command_handler
        )
        .register_handler(fail_ami_sharing_command.FailAmiSharingCommand, mock_fail_ami_sharing_command_handler),
        shared_amis_domain_qry_svc=shared_amis_domain_qry_svc,
    )
