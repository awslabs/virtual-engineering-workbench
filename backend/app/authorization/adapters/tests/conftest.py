from unittest import mock

import boto3
import botocore
import jwt
import moto
import pytest
from aws_lambda_powertools import Logger, Metrics

orig = botocore.client.BaseClient._make_api_call

TEST_REGION = "us-east-1"
TEST_POLICY_STORE_ID = "policystore-12345"
TEST_COGNITO_USER_INFO_URI = "https://cognito-idp.region.amazonaws.com/userInfo"


@pytest.fixture(scope="function", autouse=True)
def required_env_vars(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture()
def mocked_is_authorized_response():
    return {
        "decision": "ALLOW",
        "determiningPolicies": [{"policyId": "pol-123"}],
    }


@pytest.fixture()
def mock_is_authorized_denied_response():
    return {
        "decision": "DENY",
        "determiningPolicies": [{"policyId": "pol-123"}],
        "errors": [{"errorDescription": "Error"}],
    }


@pytest.fixture()
def mock_logger():
    return mock.Mock(spec=Logger)


@pytest.fixture()
def mock_metrics():
    return mock.Mock(spec=Metrics)


@pytest.fixture()
def mock_jwk_client():
    return mock.Mock(spec=jwt.PyJWKClient)


@pytest.fixture()
def mock_requests_get():
    with mock.patch("requests.get") as mock_get:
        yield mock_get


@pytest.fixture()
def mock_jwt_decode():
    with mock.patch("jwt.decode") as mock_decode:
        yield mock_decode


@pytest.fixture()
def valid_jwt_token():
    return "valid.jwt.token"


@pytest.fixture()
def invalid_jwt_token():
    return "invalid.jwt.token"


@pytest.fixture()
def mock_user_info_response():
    return {"sub": "user123", "email": "user@example.com", "custom:user_tid": "T012345"}


@pytest.fixture()
def mock_cognito_service(mock_logger, mock_metrics, mock_jwk_client):
    from app.authorization.adapters.services import cognito_service

    return cognito_service.CognitoService(
        cognito_user_info_uri=TEST_COGNITO_USER_INFO_URI,
        jwk_client=mock_jwk_client,
        logger=mock_logger,
        metrics=mock_metrics,
    )


@pytest.fixture()
def mock_avp_is_authorized_request(mocked_is_authorized_response):
    return mock.MagicMock(return_value=mocked_is_authorized_response)


@pytest.fixture()
def mock_moto_error_calls(mock_avp_is_authorized_request):
    invocations = {
        "IsAuthorized": mock_avp_is_authorized_request,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture
def mock_avp(required_env_vars):
    with moto.mock_aws():
        yield boto3.client("verifiedpermissions")
