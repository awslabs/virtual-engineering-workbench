import json
import logging
from unittest import mock

import boto3
import pytest
from attr import dataclass
from moto import mock_aws

from app.projects.domain.commands.project_accounts import (
    complete_project_account_onboarding_command,
    fail_project_account_onboarding_command,
    setup_dynamic_resources_command,
    setup_prerequisites_resources_command,
    setup_static_resources_command,
)
from app.projects.entrypoints.account_onboarding import bootstrapper
from app.shared.adapters.boto import orchestration_service
from app.shared.adapters.message_bus import in_memory_command_bus
from app.shared.domain.model import task_context
from app.shared.domain.ports import task_context_query_service


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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "AccountOnboarding")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "DOMAIN_EVENT_BUS_ARN",
        "arn:aws:events:us-east-1:001234567890:event-bus/domain-events",
    )
    monkeypatch.setenv("BOUNDED_CONTEXT", "Projects")
    monkeypatch.setenv("ACCOUNT_BOOTSTRAP_ROLE", "AccountBootstrapRole")
    monkeypatch.setenv("DNS_RECORDS_PARAM_NAME", "/test/param")
    monkeypatch.setenv("ECS_CONTAINER_METADATA_URI_V4", "https://test")
    monkeypatch.setenv("ZONE_NAME", "example.com")
    monkeypatch.setenv("TABLE_NAME", "test-table")
    monkeypatch.setenv("GSI_NAME_ENTITIES", "gsi_entities")
    monkeypatch.setenv("GSI_NAME_AWS_ACCOUNTS", "gsi_accounts")
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", "gsi_inverted_pk")
    monkeypatch.setenv("ACCOUNT_SSM_PARAMETERS_PATH_PREFIX", "acc-ssm-param-prefix")
    monkeypatch.setenv("VPC_ID_SSM_PARAMETER_NAME", "vpc-id-ssm-param-name")
    monkeypatch.setenv("VPC_TAG", "vpc-tag")


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
def mock_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name="/test/param",
        Type="String",
        Value=json.dumps(
            {
                "records": [
                    {
                        "name": "www",
                        "ttl": 300,
                        "type": "CNAME",
                        "value": {
                            "us-east-1": "www.test.com.",
                        },
                    },
                ],
            },
        ),
    )


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture()
def task_context_qry_srv_mock():
    qry_svc = mock.create_autospec(spec=task_context_query_service.TaskContextQueryService)
    qry_svc.get_task_context.return_value = task_context.TaskContext(
        aws_request_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        function_name="test",
        function_version="v2",
        log_group_name="test-log-group",
        log_stream_name="test-log-stream",
        invoked_function_arn="arn:aws:lambda:eu-west-1:000000000:function:test",
        memory_limit_in_mb=128,
    )
    return qry_svc


@pytest.fixture()
def sfn_service_mock():
    return mock.create_autospec(spec=orchestration_service.OrchestrationService)


@pytest.fixture
def setup_prerequisites_resources_command_mock():
    return mock.Mock()


@pytest.fixture
def setup_dynamic_resources_command_mock():
    return mock.Mock()


@pytest.fixture
def setup_static_resources_command_mock():
    return mock.Mock()


@pytest.fixture
def complete_onboard_command_mock():
    return mock.Mock()


@pytest.fixture
def fail_onboard_command_mock():
    return mock.Mock()


@pytest.fixture
def mock_dependencies(
    mock_logger,
    task_context_qry_srv_mock,
    setup_prerequisites_resources_command_mock,
    setup_dynamic_resources_command_mock,
    setup_static_resources_command_mock,
    complete_onboard_command_mock,
    fail_onboard_command_mock,
    sfn_service_mock,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            setup_prerequisites_resources_command.SetupPrerequisitesResourcesCommand,
            setup_prerequisites_resources_command_mock,
        )
        .register_handler(
            setup_dynamic_resources_command.SetupDynamicResourcesCommand,
            setup_dynamic_resources_command_mock,
        )
        .register_handler(
            setup_static_resources_command.SetupStaticResourcesCommand,
            setup_static_resources_command_mock,
        )
        .register_handler(
            complete_project_account_onboarding_command.CompleteProjectAccountOnboarding,
            complete_onboard_command_mock,
        )
        .register_handler(
            fail_project_account_onboarding_command.FailProjectAccountOnboarding,
            fail_onboard_command_mock,
        ),
        task_context_qry_srv=task_context_qry_srv_mock,
        step_functions_service=sfn_service_mock,
    )


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.projects.entrypoints.account_onboarding.bootstrapper.migrations_config",
        return_value=[],
    ):
        yield
