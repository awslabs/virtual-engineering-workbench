import io
import json
import logging
import unittest
from datetime import datetime
from enum import Enum
from typing import Optional
from unittest import mock

import boto3
import botocore
import moto
import pytest

from app.shared.adapters.boto import aws_secrets_service, boto_provider
from app.shared.adapters.boto.dict_context_provider import DictCtxProvider
from app.shared.domain.model import task_context

orig = botocore.client.BaseClient._make_api_call


class GlobalVariables(Enum):
    AWS_ACCESS_KEY_ID: str = "aws-access-key-id"
    AWS_ACCOUNT_ID: str = "123456789012"
    AWS_ROLE_NAME: str = "aws-role-name"
    AWS_SECRET_ACCESS_KEY: str = "aws-secret-access-key"
    AWS_SESSION_NAME: str = "aws-session-name"
    AWS_SESSION_TOKEN: str = "aws-session-token"
    DEFAULT_MEMORY_LIMIT_IN_MB: int = -1
    DESCRIPTION: str = "description"
    REGION_NAME: str = "us-east-1"
    SECRET_NAME: str = "secret-name"
    SECRET_PATH: str = "/secret-path"
    SECRET_VALUE: str = "secret-value"
    URL: str = "https://url.com"


@pytest.fixture
def get_test_container_metadata():
    def __get_test_container_metadata(
        awslogs_group: str = "/ecs/metadata",
        awslogs_stream: str = "ecs/curl/8f03e41243824aea923aca126495f665",
        limits: bool = True,
        memory: Optional[int] = 128,
    ):
        container_metadata = {
            "LogOptions": {
                "awslogs-group": awslogs_group,
                "awslogs-stream": awslogs_stream,
            },
        }
        if limits:
            container_metadata["Limits"] = {}
            if memory:
                container_metadata["Limits"]["Memory"] = memory

        return io.BytesIO(json.dumps(container_metadata).encode("utf-8"))

    return __get_test_container_metadata


@pytest.fixture
def get_test_task_context():
    def __get_test_task_context(
        aws_request_id: str = "158d1c8083dd49d6b527399fd6414f5c",
        function_name: str = "curltest",
        function_version: str = "26",
        log_group_name: str = "/ecs/metadata",
        log_stream_name: str = "ecs/curl/8f03e41243824aea923aca126495f665",
        invoked_function_arn: str = "arn:aws:ecs:us-west-2:111122223333:task/default/158d1c8083dd49d6b527399fd6414f5c",
        memory_limit_in_mb: int = 128,
    ):
        return task_context.TaskContext(
            aws_request_id=aws_request_id,
            function_name=function_name,
            function_version=function_version,
            log_group_name=log_group_name,
            log_stream_name=log_stream_name,
            invoked_function_arn=invoked_function_arn,
            memory_limit_in_mb=memory_limit_in_mb,
        )

    return __get_test_task_context


@pytest.fixture
def get_test_task_metadata():
    def __get_test_task_metadata(
        family: str = "curltest",
        revision: str = "26",
        taskarn: str = "arn:aws:ecs:us-west-2:111122223333:task/default/158d1c8083dd49d6b527399fd6414f5c",
    ):
        return io.BytesIO(
            json.dumps(
                {
                    "Family": family,
                    "Revision": revision,
                    "TaskARN": taskarn,
                }
            ).encode("utf-8")
        )

    return __get_test_task_metadata


@pytest.fixture()
def mock_aws_secrets_service(mock_secretsmanager_provider):
    return aws_secrets_service.AWSSecretsService(secretsmanager_provider=mock_secretsmanager_provider)


@pytest.fixture
def mock_boto_provider_options():
    return boto_provider.BotoProviderOptions(
        aws_account_id=GlobalVariables.AWS_ACCOUNT_ID.value,
        aws_region=GlobalVariables.REGION_NAME.value,
        aws_role_name=GlobalVariables.AWS_ROLE_NAME.value,
        aws_session_name=GlobalVariables.AWS_SESSION_NAME.value,
    )


@pytest.fixture
def mock_boto_provider(mock_boto_provider_options, mock_logger):
    with moto.mock_aws():
        yield boto_provider.BotoProvider(
            ctx=DictCtxProvider(),
            logger=mock_logger,
            default_options=mock_boto_provider_options,
        )


@pytest.fixture
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture()
def mock_secretsmanager_client():
    with moto.mock_aws():
        yield boto3.client(
            "secretsmanager",
            aws_access_key_id=GlobalVariables.AWS_ACCESS_KEY_ID.value,
            aws_secret_access_key=GlobalVariables.AWS_SECRET_ACCESS_KEY.value,
            aws_session_token=GlobalVariables.AWS_SESSION_TOKEN.value,
            region_name=GlobalVariables.REGION_NAME.value,
        )


@pytest.fixture()
def mock_secretsmanager_provider(mock_boto_provider):
    return mock_boto_provider.client("secretsmanager")


@pytest.fixture()
def mock_logs_client():
    with moto.mock_aws():
        yield boto3.client(
            "logs",
            aws_access_key_id=GlobalVariables.AWS_ACCESS_KEY_ID.value,
            aws_secret_access_key=GlobalVariables.AWS_SECRET_ACCESS_KEY.value,
            aws_session_token=GlobalVariables.AWS_SESSION_TOKEN.value,
            region_name=GlobalVariables.REGION_NAME.value,
        )


@pytest.fixture()
def mock_logs_provider(mock_boto_provider):
    return mock_boto_provider.client("logs")


@pytest.fixture()
def mock_aws_logs_service(mock_logs_provider):
    from app.shared.adapters.boto import aws_logs_service

    return aws_logs_service.AWSLogsService(logs_provider=mock_logs_provider)


@pytest.fixture()
def mock_moto_calls(
    mock_get_metric_data_request,
):
    invocations = {
        "GetMetricData": mock_get_metric_data_request,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with unittest.mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mock_get_metric_data_request():
    return unittest.mock.MagicMock(
        return_value={
            "MetricDataResults": [
                {
                    "Id": "cpu_usage",
                    "Label": "CPUUtilization",
                    "Timestamps": [datetime(2024, 1, 1, 0, 0), datetime(2024, 1, 1, 0, 5), datetime(2024, 1, 1, 0, 10)],
                    "Values": [45.6, 52.3, 48.9],
                    "StatusCode": "Complete",
                    "Messages": [],
                }
            ]
        }
    )
