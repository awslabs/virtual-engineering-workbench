import logging
from datetime import datetime
from unittest import mock

import boto3
import moto
import pytest
from attr import dataclass
from moto import mock_aws

from app.shared.api import secrets_manager_api

TEST_REGION = "us-east-1"
TEST_SECRET_NAME = "audit-logging-key"
TEST_TABLE_NAME = "test-table"


@pytest.fixture()
def mock_logger():
    return mock.create_autospec(spec=logging.Logger)


@pytest.fixture
def lambda_context():
    @dataclass
    class context:
        function_name = "test"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:eu-west-1:000000000:function:test"
        aws_request_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    return context


@pytest.fixture
def lambda_handler():
    def _lambda_handler(event, context):
        return {"statusCode": "200"}

    return _lambda_handler


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", TEST_REGION)
    monkeypatch.setenv("AWS_DEFAULT_REGION", TEST_REGION)


@pytest.fixture()
def cognito_identity_mock():
    with mock_aws():
        yield boto3.client("cognito-idp", region_name=TEST_REGION)


@pytest.fixture()
def cognito_user_pool_mock(cognito_identity_mock):
    return cognito_identity_mock.create_user_pool(PoolName="Test")


@pytest.fixture()
def mock_cognito_user(cognito_identity_mock, cognito_user_pool_mock):
    user = cognito_identity_mock.admin_create_user(
        UserPoolId=cognito_user_pool_mock["UserPool"]["Id"],
        Username="Kiff",
        UserAttributes=[
            {
                "Name": "email",
                "Value": "test@example.com",
            },
            {
                "Name": "sub",
                "Value": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            },
        ],
    )

    return user


@pytest.fixture()
def mock_cognito_admin_group(cognito_identity_mock, cognito_user_pool_mock):
    group = cognito_identity_mock.create_group(
        GroupName="Admin",
        UserPoolId=cognito_user_pool_mock["UserPool"]["Id"],
    )

    return group


@pytest.fixture()
def mock_cognito_group_membership(
    cognito_identity_mock,
    cognito_user_pool_mock,
    mock_cognito_user,
    mock_cognito_admin_group,
):
    response = cognito_identity_mock.admin_add_user_to_group(
        UserPoolId=cognito_user_pool_mock["UserPool"]["Id"],
        Username=mock_cognito_user["User"]["Username"],
        GroupName=mock_cognito_admin_group["Group"]["GroupName"],
    )

    return response


@pytest.fixture(autouse=True)
def mock_aws_client():
    with mock_aws():
        yield boto3.client("sts", region_name=TEST_REGION)


@pytest.fixture(autouse=True)
def mock_secrets_manager():
    with mock_aws():
        yield boto3.client(
            "secretsmanager",
            region_name=TEST_REGION,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture(autouse=True)
def mock_audit_logging_secret(mock_secrets_manager):
    secrets_manager = secrets_manager_api.SecretsManagerAPI(
        region=TEST_REGION,
        access_key_id="access_key_id",
        secret_access_key="secret_access_key",
        session_token="session_token",
    )

    return secrets_manager.create_secret(name=TEST_SECRET_NAME, value="test123")


@pytest.fixture(autouse=True)
def mock_secret(mock_secrets_manager):
    secrets_manager = secrets_manager_api.SecretsManagerAPI(
        region=TEST_REGION,
        access_key_id="access_key_id",
        secret_access_key="secret_access_key",
        session_token="session_token",
    )

    def _mock_secret(secret_name: str, secret_value: str):
        return secrets_manager.create_secret(name=secret_name, value=secret_value)

    return _mock_secret


@pytest.fixture
def test_table_name():
    return TEST_TABLE_NAME


@pytest.fixture
def mock_dynamodb():
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name="eu-central-1")


@pytest.fixture()
def backend_app_dynamodb_table(mock_dynamodb):
    table = mock_dynamodb.create_table(
        TableName=TEST_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    table.meta.client.get_waiter("table_exists").wait(TableName=TEST_TABLE_NAME)
    return table


@pytest.fixture
def mock_cloudwatch_client():
    with moto.mock_aws():
        yield boto3.client("cloudwatch", region_name="eu-central-1")


@pytest.fixture(autouse=True)
def mock_metric_data(mock_cloudwatch_client):
    mock_cloudwatch_client.put_metric_data(
        Namespace="VirtualEngineeringWorkbench",
        MetricData=[
            {
                "MetricName": "TotalAssignedUsers",
                "Dimensions": [
                    {"Name": "Program", "Value": "Test Project"},
                    {"Name": "service", "Value": "Projects"},
                ],
                "Timestamp": datetime(2015, 1, 2),
                "Value": 123,
                "Unit": "Count",
            },
            {
                "MetricName": "TotalProgramProvisionedProducts",
                "Dimensions": [
                    {"Name": "Program", "Value": "Test Project"},
                    {"Name": "service", "Value": "Provisioning"},
                ],
                "Timestamp": datetime(2015, 1, 2),
                "Value": 123,
                "Unit": "Count",
            },
            {
                "MetricName": "TotalProgramUsersWithProvisionedProducts",
                "Dimensions": [
                    {"Name": "Program", "Value": "Test Project"},
                    {"Name": "service", "Value": "Provisioning"},
                ],
                "Timestamp": datetime(2015, 1, 2),
                "Value": 123,
                "Unit": "Count",
            },
            {
                "MetricName": "TotalProgramRunningProvisionedProducts",
                "Dimensions": [
                    {"Name": "Program", "Value": "Test Project"},
                    {"Name": "service", "Value": "Provisioning"},
                ],
                "Timestamp": datetime(2015, 1, 2),
                "Value": 123,
                "Unit": "Count",
            },
            {
                "MetricName": "TotalProgramCurrentActiveUsers",
                "Dimensions": [
                    {"Name": "Program", "Value": "Test Project"},
                    {"Name": "service", "Value": "Provisioning"},
                ],
                "Timestamp": datetime(2015, 1, 2),
                "Value": 123,
                "Unit": "Count",
            },
        ],
    )


@pytest.fixture
def mock_s3_client():
    with moto.mock_aws():
        yield boto3.client("s3", region_name="eu-central-1")
