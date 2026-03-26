import logging
from unittest import mock

import boto3
import moto
import pytest
from attr import dataclass


@pytest.fixture
def mock_table_name():
    return "TEST"


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
def aws_credentials(monkeypatch, mock_table_name):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ProjectsEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BOUNDED_CONTEXT", "authorization")
    monkeypatch.setenv("TABLE_NAME", mock_table_name)
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", "")


@pytest.fixture
def generate_event():
    def _generate_event(detail_type: str, detail: dict):
        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": detail_type,
            "source": "org.workbench.provisioning.dev",
            "account": "123456789012",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": [],
            "detail": detail,
        }

    return _generate_event


@pytest.fixture
def enrolment_approved_event():
    return {
        "eventName": "EnrolmentApproved",
        "programId": "proj-123",
        "programName": "Test Program",
        "userId": "test-user-id",
        "userEmail": "user@example.doesnotexist",
        "enrolmentId": "enrolment-id",
        "roles": ["PLATFORM_USER"],
        "groupMemberships": ["VEW_USERS"],
    }


@pytest.fixture
def user_assigned_event():
    return {
        "eventName": "UserAssigned",
        "projectId": "proj-123",
        "userId": "test-user-id",
        "roles": ["PLATFORM_USER"],
        "groupMemberships": ["VEW_USERS"],
    }


@pytest.fixture
def user_reassigned_event():
    return {
        "eventName": "UserReAssigned",
        "projectId": "proj-123",
        "userId": "test-user-id",
        "roles": ["PLATFORM_USER"],
        "groupMemberships": ["VEW_USERS"],
    }


@pytest.fixture
def user_unassigned_event():
    return {
        "eventName": "UserUnAssigned",
        "projectId": "proj-123",
        "userId": "test-user-id",
    }


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def gsi_name_inverted_pk():
    return "GSI1"


@pytest.fixture()
def backend_app_dynamodb_table(mock_dynamodb, mock_table_name, gsi_name_inverted_pk):
    table = mock_dynamodb.create_table(
        TableName=mock_table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": gsi_name_inverted_pk,
                "KeySchema": [
                    {"AttributeName": "SK", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    )

    table.meta.client.get_waiter("table_exists").wait(TableName=mock_table_name)
    return table


@pytest.fixture
def mock_dynamodb():
    with moto.mock_aws():
        yield boto3.resource("dynamodb")
