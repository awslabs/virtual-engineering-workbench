import json
import logging
from enum import Enum
from unittest import mock

import boto3
import pytest
from attr import dataclass
from moto import mock_aws

from app.packaging.domain.commands.component import (
    check_component_version_testing_environment_launch_status_command,
    check_component_version_testing_environment_setup_status_command,
    check_component_version_testing_test_status_command,
    complete_component_version_testing_command,
    launch_component_version_testing_environment_command,
    run_component_version_testing_command,
    setup_component_version_testing_environment_command,
)
from app.packaging.entrypoints.component_version_testing import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus


class GlobalVariables(Enum):
    TEST_AMI_FACTORY_SUBNET_NAMES = "subnet-1a,subnet-1b"


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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Componenttesting")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BOUNDED_CONTEXT", "Packaging")
    monkeypatch.setenv("ADMIN_ROLE", "Admin")
    monkeypatch.setenv("AMI_FACTORY_AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("AMI_FACTORY_VPC_NAME", "vpc-test")
    monkeypatch.setenv("INSTANCE_SECURITY_GROUP_NAME", "sg-test")
    monkeypatch.setenv("SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME", "/test/param")
    monkeypatch.setenv("TABLE_NAME", "TestTable")
    monkeypatch.setenv("VOLUME_SIZE", "500")
    monkeypatch.setenv("SSM_RUN_COMMAND_TIMEOUT", "60")
    monkeypatch.setenv("AMI_FACTORY_SUBNET_NAMES", GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value)


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
                "Linux": {
                    "amd64": {
                        "Ubuntu 24": {
                            # Adding /test/ prefix since /aws/service/ is reserved and can't be mocked
                            "ami_ssm_param_name": "/test/aws/service/canonical/ubuntu/server/20.04/stable/current/amd64/hvm/ebs-gp2/ami-id",
                            "command_ssm_document_name": "AWS-RunShellScript",
                            "instance_type": "m8i.2xlarge",
                            "run_testing_command": "awstoe run --documents << documents >> --execution-id /<< instance_id >> --log-s3-bucket-name << log_s3_bucket_name >> --log-s3-key-prefix << object_id >>/<< version_id >> --trace",
                            "setup_testing_environment_command": "curl https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/amd64/awstoe --output /usr/bin/awstoe && chmod +x /usr/bin/awstoe",
                        },
                    },
                },
            }
        ),
    )


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture()
def mock_component_id():
    return "comp-12345abc"


@pytest.fixture()
def mock_component_version_id():
    return "version-12345abc"


@pytest.fixture()
def mock_test_execution_id():
    return "0be91e9a-caed-4c4c-8072-f7c203cea24e"


@pytest.fixture()
def mock_instance_ids():
    return [
        "i-01234567890abcdef",
        "i-56789012345ghijkl",
    ]


@pytest.fixture()
def mock_instances_status():
    return "CONNECTED"


@pytest.fixture()
def mock_command_ids():
    return [
        "abcd1234-ef56-gh78-ij90-klmnop123456",
        "efgh5678-ij90-kl12-mn34-opqrst567890",
    ]


@pytest.fixture()
def mock_commands_status():
    return "SUCCESS"


@pytest.fixture()
def mock_component_version_test_status():
    return "SUCCESS"


@pytest.fixture
def mock_launch_component_version_testing_environment_command_handler(
    mock_instance_ids,
):
    launch_component_version_testing_environment_command = mock.Mock()

    return launch_component_version_testing_environment_command


@pytest.fixture
def mock_check_component_version_testing_environment_launch_status_command_handler(
    mock_instances_status,
):
    check_component_version_testing_environment_launch_status_command = mock.Mock()
    check_component_version_testing_environment_launch_status_command.return_value = mock_instances_status

    return check_component_version_testing_environment_launch_status_command


@pytest.fixture
def mock_run_component_version_testing_command_handler(mock_command_ids):
    run_component_version_testing_command = mock.Mock()
    run_component_version_testing_command.return_value = mock_command_ids

    return run_component_version_testing_command


@pytest.fixture
def mock_check_component_version_testing_environment_setup_status_command_handler(
    mock_commands_status,
):
    check_component_version_testing_environment_setup_status_command = mock.Mock()
    check_component_version_testing_environment_setup_status_command.return_value = mock_commands_status

    return check_component_version_testing_environment_setup_status_command


@pytest.fixture
def mock_setup_component_version_testing_environment_command_handler(mock_command_ids):
    setup_component_version_testing_environment_command = mock.Mock()
    setup_component_version_testing_environment_command.return_value = mock_command_ids

    return setup_component_version_testing_environment_command


@pytest.fixture
def mock_check_component_version_testing_test_status_command_handler(
    mock_commands_status,
):
    check_component_version_testing_test_status_command = mock.Mock()
    check_component_version_testing_test_status_command.return_value = mock_commands_status

    return check_component_version_testing_test_status_command


@pytest.fixture
def mock_complete_component_version_testing_command_handler(
    mock_component_version_test_status,
):
    complete_component_version_testing_command = mock.Mock()
    complete_component_version_testing_command.return_value = mock_component_version_test_status

    return complete_component_version_testing_command


@pytest.fixture
def mock_dependencies(
    mock_logger,
    mock_launch_component_version_testing_environment_command_handler,
    mock_check_component_version_testing_environment_launch_status_command_handler,
    mock_setup_component_version_testing_environment_command_handler,
    mock_check_component_version_testing_environment_setup_status_command_handler,
    mock_run_component_version_testing_command_handler,
    mock_check_component_version_testing_test_status_command_handler,
    mock_complete_component_version_testing_command_handler,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            launch_component_version_testing_environment_command.LaunchComponentVersionTestingEnvironmentCommand,
            mock_launch_component_version_testing_environment_command_handler,
        )
        .register_handler(
            check_component_version_testing_environment_launch_status_command.CheckComponentVersionTestingEnvironmentLaunchStatusCommand,
            mock_check_component_version_testing_environment_launch_status_command_handler,
        )
        .register_handler(
            setup_component_version_testing_environment_command.SetupComponentVersionTestingEnvironmentCommand,
            mock_setup_component_version_testing_environment_command_handler,
        )
        .register_handler(
            check_component_version_testing_environment_setup_status_command.CheckComponentVersionTestingEnvironmentSetupStatusCommand,
            mock_check_component_version_testing_environment_setup_status_command_handler,
        )
        .register_handler(
            run_component_version_testing_command.RunComponentVersionTestingCommand,
            mock_run_component_version_testing_command_handler,
        )
        .register_handler(
            check_component_version_testing_test_status_command.CheckComponentVersionTestingTestStatusCommand,
            mock_check_component_version_testing_test_status_command_handler,
        )
        .register_handler(
            complete_component_version_testing_command.CompleteComponentVersionTestingCommand,
            mock_complete_component_version_testing_command_handler,
        ),
    )
