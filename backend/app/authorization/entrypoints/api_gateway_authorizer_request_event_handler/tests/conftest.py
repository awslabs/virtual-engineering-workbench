import io
import json
from dataclasses import dataclass
from datetime import datetime
from unittest import mock

import boto3
import botocore
import jwt
import moto
import mypy_boto3_ssm
import pytest
import requests_mock
from cryptography.hazmat.primitives.asymmetric import rsa
from freezegun import freeze_time
from moto import mock_aws

from app.authorization.adapters.repository import dynamo_entity_config
from app.authorization.domain.read_models import project_assignment
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

orig = botocore.client.BaseClient._make_api_call

TEST_REGION = "us-east-1"
TEST_SECRET_NAME = "audit-logging-key"
TEST_PARAM_PREFIX = "/param/prefix/{api_id}"


@pytest.fixture
def mocked_projects_url():
    return "https://fake-projects.nonexisting/"


@pytest.fixture
def mocked_user_pool_url():
    return "https://fake.nonexisting"


@pytest.fixture
def mocked_user_pool_id():
    return "fake_user_pool_id"


@pytest.fixture
def mocked_user_pool_region():
    return "us-east-1"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch, mocked_user_pool_url, mocked_user_pool_id, mock_table_name, mocked_user_pool_region):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT", "123456789012")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Projects")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("API_BASE_PATH", "communication")
    monkeypatch.setenv("POLICY_STORE_SSM_PARAM_PREFIX", TEST_PARAM_PREFIX.format(api_id=""))
    monkeypatch.setenv("USER_ROLE_STAGE_ACCESS_SSM_PARAM", "user-access-cfg-param")
    monkeypatch.setenv("JWKS_URI", "https://example.com")
    monkeypatch.setenv("JWK_TIMEOUT", "3")
    monkeypatch.setenv("USER_POOL_URL", mocked_user_pool_url)
    monkeypatch.setenv("USER_POOL_ID", mocked_user_pool_id)
    monkeypatch.setenv("USER_POOL_REGION", mocked_user_pool_region)
    monkeypatch.setenv("USER_POOL_CLIENT_IDS", "test-client-id,test-client-id-2")
    monkeypatch.setenv("TABLE_NAME", mock_table_name)
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", "gsi_inverted_pk")


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
def mock_auth_event(user_auth_jwt):
    def __inner(authorization=user_auth_jwt, path_parameters={"projectId": "proj-123"}):
        return {
            "type": "REQUEST",
            "methodArn": "arn:aws:execute-api:us-east-1:123:abcdef/v1/GET/projects",
            "resource": "/projects/{projectId}",
            "path": "/projects/projects",
            "httpMethod": "GET",
            "headers": {
                "authorization": authorization,
            },
            "multiValueHeaders": {
                "authorization": [authorization],
            },
            "queryStringParameters": {"pageSize": "10"},
            "multiValueQueryStringParameters": {"pageSize": ["10"]},
            "pathParameters": path_parameters,
            "stageVariables": {},
            "requestContext": {
                "resourceId": "abcd",
                "resourcePath": "/projects/{projectId}",
                "operationName": "GetProject",
                "httpMethod": "GET",
                "extendedRequestId": "abcd",
                "requestTime": "07/Apr/2025:15:18:19 +0000",
                "path": "/projects/projects",
                "accountId": "01234567890",
                "protocol": "HTTP/1.1",
                "stage": "v1",
                "domainPrefix": "api",
                "requestTimeEpoch": 1744039099089,
                "requestId": "fd7cb48a-0fd0-43cf-9f96-510fd20a84d1",
                "identity": {},
                "domainName": "",
                "deploymentId": "123",
                "apiId": "rest-api-id",
            },
        }

    return __inner


@pytest.fixture()
def ssm_mock():
    with mock_aws():
        yield boto3.client("ssm", region_name=TEST_REGION)


@pytest.fixture(autouse=True)
def mock_moto_calls(mock_avp_is_authorized_request):
    invocations = {
        "IsAuthorized": mock_avp_is_authorized_request,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture(autouse=True)
def mock_avp(aws_credentials):
    with moto.mock_aws():
        yield boto3.client("verifiedpermissions")


@pytest.fixture
def mock_logger():
    return mock.Mock()


@pytest.fixture
def mock_metrics():
    return mock.Mock()


@pytest.fixture()
def mock_jwk_client():
    return mock.Mock(spec=jwt.PyJWKClient)


@pytest.fixture
def mock_requests():
    with requests_mock.Mocker() as mock:
        yield mock


@pytest.fixture()
def mock_jwt_decode():
    with mock.patch("jwt.decode") as mock_decode:
        yield mock_decode


@pytest.fixture(autouse=True)
def mock_api_policy_stores(ssm_mock: mypy_boto3_ssm.Client, mocked_projects_url):
    [
        ssm_mock.put_parameter(
            Name=TEST_PARAM_PREFIX.format(api_id=p),
            Value=json.dumps(
                {
                    "api_id": f"api-{p}",
                    "policy_store_id": f"pol-{p}",
                    "bounded_context": f"bc-{p}",
                    "api_url": "mock://fake-url.nonexisting",
                    "auth_features": ["ProjectAssignments"],
                }
            ),
            Type="String",
        )
        for p in range(2)
    ]
    ssm_mock.put_parameter(
        Name=TEST_PARAM_PREFIX.format(api_id="unit-test"),
        Value=json.dumps(
            {
                "api_id": "rest-api-id",
                "policy_store_id": "policy-store-id",
                "bounded_context": "projects",
                "api_url": mocked_projects_url,
                "auth_features": ["ProjectAssignments"],
            }
        ),
        Type="String",
    )


@pytest.fixture(autouse=True)
def mock_access_cfg(ssm_mock: mypy_boto3_ssm.Client):
    ssm_mock.put_parameter(
        Name="user-access-cfg-param",
        Value=json.dumps(
            {
                "PLATFORM_USER": ["prod"],
                "ADMIN": ["prod", "dev", "qa"],
            }
        ),
        Type="String",
    )


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
def valid_jwt_token():
    return "valid.jwt.token"


@pytest.fixture()
def invalid_jwt_token():
    return "invalid.jwt.token"


@pytest.fixture
def mock_user_info_endpoint(mock_requests, mocked_user_pool_url, mocked_user_info_success_response):
    return mock_requests.get(
        f"{mocked_user_pool_url}/oauth2/userInfo", status_code=200, json=mocked_user_info_success_response()
    )


@pytest.fixture
def mock_user_info_endpoint_401(mock_requests, mocked_user_pool_url, mocked_user_info_success_response):
    return mock_requests.get(
        f"{mocked_user_pool_url}/oauth2/userInfo",
        status_code=401,
    )


@pytest.fixture
def mocked_user_info_success_response():
    def _mocked_user_info_success_response(user_tid: str = "T00112233"):
        return {"sub": "user123", "custom:user_tid": user_tid, "email": "test@test.com"}

    return _mocked_user_info_success_response


@pytest.fixture()
def mock_avp_is_authorized_request(mocked_is_authorized_response):
    return mock.MagicMock(return_value=mocked_is_authorized_response)


@pytest.fixture
def jwt_test_private_key():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )


@pytest.fixture
def jwt_test_public_key(jwt_test_private_key):
    return jwt_test_private_key.public_key()


@pytest.fixture
def jwt_correct_kid():
    return "230498151c214b788dd97f22b85410a5"


@pytest.fixture
def user_auth_jwt(jwt_test_private_key, jwt_correct_kid, mocked_user_pool_id, mocked_user_pool_region):
    payload = {
        "exp": datetime.fromisoformat("2025-05-02 10:00:00+00:00").timestamp(),
        "iss": f"https://cognito-idp.{mocked_user_pool_region}.amazonaws.com/{mocked_user_pool_id}",
        "token_use": "access",
        "aud": "test-client-id",
    }
    headers = {"kid": jwt_correct_kid}
    return "Bearer " + jwt.encode(payload, jwt_test_private_key, algorithm="RS256", headers=headers)


@pytest.fixture
def mocked_jwks_response(jwt_test_public_key, jwt_correct_kid):
    alg = jwt.algorithms.RSAAlgorithm(jwt.algorithms.RSAAlgorithm.SHA256)
    pub_key = alg.prepare_key(jwt_test_public_key)
    jwk = alg.to_jwk(pub_key, True)

    return io.StringIO(json.dumps({"keys": [{**jwk, "kid": jwt_correct_kid}]}))


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
                "KeySchema": [{"AttributeName": "SK", "KeyType": "HASH"}, {"AttributeName": "PK", "KeyType": "RANGE"}],
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


@pytest.fixture
def mocked_ddb_uow(mock_table_name, mock_dynamodb, backend_app_dynamodb_table):
    return dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=mock_table_name).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture
def mocked_assignments_data(mocked_ddb_uow):
    def __inner(
        user_id: str = "T00112233",
        roles=["PLATFORM_USER"],
        active_directory_groups=[{"domain": "TEST_DOMAIN"}],
        group_memberships=["VEW_USERS"],
    ):
        with mocked_ddb_uow:
            mocked_ddb_uow.get_repository(project_assignment.AssignmentPrimaryKey, project_assignment.Assignment).add(
                project_assignment.Assignment(
                    userId=user_id,
                    projectId="proj-123",
                    roles=roles,
                    activeDirectoryGroups=active_directory_groups,
                    groupMemberships=group_memberships,
                )
            )
            mocked_ddb_uow.commit()

    return __inner


@pytest.fixture
def mock_table_name():
    return "test-table"


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-01-01 12:00:00"):
        yield
