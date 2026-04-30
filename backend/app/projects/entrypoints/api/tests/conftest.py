import json
import logging
import os
from unittest import mock

import boto3
import pytest
from attr import dataclass
from moto import mock_aws
from openapi_spec_validator.readers import read_from_filename

from app.shared.api import secrets_manager_api

TEST_REGION = "us-east-1"
TEST_ORG_PREFIX = "proserve"
TEST_APP_PREFIX = "wb"
TEST_ENVIRONMENT = "dev"
TEST_SECRET_NAME = "audit-logging-key"
TEST_TABLE_NAME = "TEST"
GSI_NAME = "gsi_inverted_primary_key"
GSI_AWS_ACCOUNTS = "gsi_aws_accounts"
GSI_ENTITIES = "entities"
GSI_QPK = "qpk_query_key"
GSI_QSK = "qsk_query_key"


@pytest.fixture()
def test_table_name():
    return TEST_TABLE_NAME


@pytest.fixture()
def gsi_name():
    return GSI_NAME


@pytest.fixture()
def gsi_aws_accounts():
    return GSI_AWS_ACCOUNTS


@pytest.fixture()
def gsi_entities():
    return GSI_ENTITIES


@pytest.fixture()
def gsi_qpk():
    return GSI_QPK


@pytest.fixture()
def gsi_qsk():
    return GSI_QSK


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
    monkeypatch.setenv("IMAGE_SERVICE_ACCOUNT_ID", "012345678900")
    monkeypatch.setenv("TABLE_NAME", TEST_TABLE_NAME)
    monkeypatch.setenv("GSI_NAME_ENTITIES", GSI_ENTITIES)
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", GSI_NAME)
    monkeypatch.setenv("GSI_NAME_AWS_ACCOUNTS", GSI_AWS_ACCOUNTS)
    monkeypatch.setenv("GSI_NAME_QPK", GSI_QPK)
    monkeypatch.setenv("GSI_NAME_QSK", GSI_QSK)
    monkeypatch.setenv("TOOLCHAIN_ACCOUNTS_IDS_PARAMETER_NAME", "/test/param-accounts")
    monkeypatch.setenv("VEW_ORGANIZATION_PREFIX", TEST_ORG_PREFIX)
    monkeypatch.setenv("VEW_APPLICATION_PREFIX", TEST_APP_PREFIX)
    monkeypatch.setenv("APP_ENVIRONMENT", TEST_ENVIRONMENT)


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
        Name="/test/param-accounts",
        Type="String",
        Value=json.dumps(
            {
                "us-east-1": "012345678900",
            },
        ),
    )


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch("app.projects.entrypoints.api.bootstrapper.migrations_config", return_value=[]):
        yield


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
def mock_cognito_user_group(cognito_identity_mock, cognito_user_pool_mock):
    group = cognito_identity_mock.create_group(
        GroupName="Users",
        UserPoolId=cognito_user_pool_mock["UserPool"]["Id"],
    )

    return group


@pytest.fixture(autouse=True)
def mock_cognito_group_membership(
    cognito_identity_mock, cognito_user_pool_mock, mock_cognito_user, mock_cognito_admin_group, mock_cognito_user_group
):
    response = cognito_identity_mock.admin_add_user_to_group(
        UserPoolId=cognito_user_pool_mock["UserPool"]["Id"],
        Username=mock_cognito_user["User"]["Username"],
        GroupName=mock_cognito_admin_group["Group"]["GroupName"],
    )

    user_response = cognito_identity_mock.admin_add_user_to_group(
        UserPoolId=cognito_user_pool_mock["UserPool"]["Id"],
        Username=mock_cognito_user["User"]["Username"],
        GroupName=mock_cognito_user_group["Group"]["GroupName"],
    )

    return [response, user_response]


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
def authenticated_event(cognito_user_pool_mock, mock_cognito_user):
    user_sub_ettribute = [x for x in mock_cognito_user["User"]["Attributes"] if x["Name"].lower() == "sub"][0]

    def _authenticated_event(body, path, http_method, query_params=None):
        return {
            "resource": path,
            "path": path,
            "httpMethod": http_method,
            "headers": {"Accept": "application/json", "Authorization": "Bearer eyjjdjdjdjd"},
            "multiValueHeaders": {"Accept": ["application/json"]},
            "queryStringParameters": query_params,
            "multiValueQueryStringParameters": (
                {key: [val] for key, val in query_params.items()} if query_params else None
            ),
            "pathParameters": {"proxy": ""},
            "stageVariables": None,
            "requestContext": {
                "authorizer": {
                    "userName": "USER123",
                    "userEmail": "leto@atreides.com",
                    "stages": '["dev", "qa", "prod"]',
                    "userRoles": '["ADMIN"]',
                    "userDomains": '["DOMAIN"]',
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
                    "cognitoIdentityPoolId": "us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "accountId": "111111111111",
                    "cognitoIdentityId": "us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "caller": "AROXXXXXXXXXXXXXXXXX:CognitoIdentityCredentials",
                    "sourceIp": "0.0.0.0",
                    "principalOrgId": "o-123",
                    "accessKey": "AXXXXXXXXXXXXXXXXXXXXX",
                    "cognitoAuthenticationType": "authenticated",
                    "cognitoAuthenticationProvider": f"cognito-idp.us-east-1.amazonaws.com/us-east-1_lqYSBenxm,cognito-idp.us-east-1.amazonaws.com/{cognito_user_pool_mock['UserPool']['Id']}:CognitoSignIn:{user_sub_ettribute['Value']}",
                    "userArn": "arn:aws:sts::111111111111:assumed-role/Test-Cognito-Group/CognitoIdentityCredentials",
                    "userAgent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/0.0.0.0 Safari/537.36",
                    "user": "AROXXXXXXXXXXXXXXXXX:CognitoIdentityCredentials",
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
        "proserve-workbench-projects-api-schema.yaml",
    )
    spec_dict, base_uri = read_from_filename(schema_path)
    return spec_dict


@pytest.fixture()
def mock_logger():
    mock_logger = mock.create_autospec(spec=logging.Logger)
    return mock_logger
