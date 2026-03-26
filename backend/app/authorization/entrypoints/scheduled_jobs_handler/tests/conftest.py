import json
import logging
from unittest import mock

import boto3
import mypy_boto3_ssm
import pytest
from attr import dataclass
from moto import mock_aws

TEST_TABLE_NAME = "TEST"
TEST_PARAM_PREFIX = "/param/prefix/{api_id}"


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
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ScheduledJobEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BOUNDED_CONTEXT", "authorization")
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", "gsi_inverted_pk")
    monkeypatch.setenv("POLICY_STORE_SSM_PARAM_PREFIX", TEST_PARAM_PREFIX.format(api_id=""))


@pytest.fixture
def assignment_sync_job_event():
    return {"jobName": "AssignmentsSyncJob"}


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture()
def ssm_mock():
    with mock_aws():
        yield boto3.client("ssm")


@pytest.fixture(autouse=True)
def mock_api_policy_stores(ssm_mock: mypy_boto3_ssm.Client, mocked_projects_url):
    ssm_mock.put_parameter(
        Name=TEST_PARAM_PREFIX.format(api_id="unit-test"),
        Value=json.dumps(
            {
                "api_id": "rest-api-id",
                "policy_store_id": "policy-store-id",
                "bounded_context": "projects",
                "api_url": mocked_projects_url,
            }
        ),
        Type="String",
    )


@pytest.fixture
def mocked_projects_url():
    return "https://fake-projects.nonexisting/"
