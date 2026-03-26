import os
from unittest import mock

import boto3
import pytest
from attr import dataclass
from moto import mock_aws
from openapi_spec_validator.readers import read_from_filename

from app.shared.api import secrets_manager_api

TEST_REGION = "us-east-1"
TEST_SECRET_NAME = "audit-logging-key"
TEST_TABLE_NAME = "TEST"
GSI_ENTITIES = "entities"


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
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Projects")
    monkeypatch.setenv("AUDIT_LOGGING_KEY_NAME", TEST_SECRET_NAME)
    monkeypatch.setenv("TABLE_NAME", TEST_TABLE_NAME)
    monkeypatch.setenv("GSI_NAME_ENTITIES", GSI_ENTITIES)


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch("app.projects.entrypoints.s2s_api.bootstrapper.migrations_config", return_value=[]):
        yield


@pytest.fixture
def authenticated_event():
    def _authenticated_event(body, path, http_method, query_params=None):
        return {
            "resource": path,
            "path": path,
            "httpMethod": http_method,
            "headers": {"Accept": "application/json", "Authorization": "Bearer eyjjdjdjdjd"},
            "multiValueHeaders": {"Accept": ["application/json"]},
            "Authorization": ["Bearer eyjjdjdjdjd"],
            "queryStringParameters": query_params,
            "multiValueQueryStringParameters": None,
            "pathParameters": {"proxy": ""},
            "stageVariables": None,
            "requestContext": {
                "authorizer": {
                    "claims": {
                        "sub": "fake_client_id",
                        "token_use": "access",
                        "scope": "projects/read",
                        "auth_time": "1681464958",
                        "iss": "cognito",
                        "exp": "Fri Apr 14 10:35:58 UTC 2023",
                        "iat": "Fri Apr 14 09:35:58 UTC 2023",
                        "version": "2",
                        "jti": "1b181427-f5ea-40af-b10d-7f7d789473eb",
                        "client_id": "fake_client_id",
                    }
                },
                "resourceId": "jcjzu1",
                "resourcePath": path,
                "httpMethod": http_method,
                "extendedRequestId": "AAAAsH-rFiAFpyQ=",
                "requestTime": "17/Jun/2021:15:34:02 +0000",
                "path": path,
                "accountId": "111111111111",
                "protocol": "HTTP/1.1",
                "stage": "test-invoke-stage",
                "domainPrefix": "testPrefix",
                "requestTimeEpoch": 1623944042664,
                "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
                "identity": {
                    "cognitoIdentityPoolId": "null",
                    "accountId": "null",
                    "cognitoIdentityId": "null",
                    "caller": "null",
                    "sourceIp": "0.0.0.0",
                    "principalOrgId": "",
                    "accessKey": "null",
                    "cognitoAuthenticationType": "authenticated",
                    "cognitoAuthenticationProvider": "null",
                    "userArn": "null",
                    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/0.0.0.0 Safari/537.36",
                    "user": "null",
                },
                "apiId": "xxxxxxxxxx",
            },
            "version": "1.00",
            "body": body,
            "isBase64Encoded": False,
        }

    return _authenticated_event


@pytest.fixture
def api_schema():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(
        current_dir,
        "..",
        "schema",
        "proserve-workbench-s2s-projects-api-schema.yaml",
    )
    spec_dict, base_uri = read_from_filename(schema_path)
    return spec_dict


@pytest.fixture(autouse=True)
def mock_secrets_manager():
    with mock_aws():
        yield boto3.client(
            "secretsmanager",
            region_name=TEST_REGION,
        )


@pytest.fixture(autouse=True)
def mock_audit_logging_secret(mock_secrets_manager):
    secrets_manager = secrets_manager_api.SecretsManagerAPI(
        region=TEST_REGION,
    )

    return secrets_manager.create_secret(name=TEST_SECRET_NAME, value="test123")
