import os
import unittest.mock

import boto3
import pytest
from attr import dataclass
from moto import mock_aws
from openapi_spec_validator.readers import read_from_filename

from app.provisioning.domain.query_services import (
    products_domain_query_service,
    provisioned_products_domain_query_service,
    versions_domain_query_service,
)
from app.provisioning.entrypoints.s2s_api import bootstrapper
from app.shared.adapters.message_bus import command_bus
from app.shared.api import secrets_manager_api

TEST_REGION = "us-east-1"
TEST_SECRET_NAME = "audit-logging-key"


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
    monkeypatch.setenv("AWS_REGION", TEST_REGION)
    monkeypatch.setenv("AWS_DEFAULT_REGION", TEST_REGION)
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Projects")
    monkeypatch.setenv("AUDIT_LOGGING_KEY_NAME", TEST_SECRET_NAME)
    monkeypatch.setenv("API_BASE_PATH", "provisioning")
    monkeypatch.setenv(
        "APPLICATION_VERSION_FRONTEND_PARAMETER_NAME",
        "/proserve-wb-provisioning-api/application_version_frontend",
    )
    monkeypatch.setenv(
        "APPLICATION_VERSION_BACKEND_PARAMETER_NAME",
        "/proserve-wb-provisioning-api/application_version_backend",
    )
    monkeypatch.setenv(
        "EXPERIMENTAL_PROVISIONED_PRODUCT_PER_PROJECT_LIMIT_PARAMETER_NAME",
        "/proserve-wb-provisioning-api/experimental-provisioned-product-per-project-limit",
    )
    monkeypatch.setenv("SPOKE_ACCOUNT_VPC_ID_PARAM_NAME", "/workbench/vpc/vpc-id")
    monkeypatch.setenv("PROVISIONING_SUBNET_SELECTOR", "PrivateSubnetWithTransitGateway")
    monkeypatch.setenv("DEFAULT_PAGE_SIZE", "100")


@pytest.fixture()
def cognito_identity_mock():
    with mock_aws():
        yield boto3.client("cognito-idp", region_name=TEST_REGION)


@pytest.fixture()
def cognito_user_pool_mock(cognito_identity_mock):
    return cognito_identity_mock.create_user_pool(PoolName="Test")


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
def mock_application_version_backend_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name="/proserve-wb-provisioning-api/application_version_backend",
        Value="v1.0.0",
        Type="String",
    )


@pytest.fixture(autouse=True)
def mock_application_version_frontend_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name="/proserve-wb-provisioning-api/application_version_frontend",
        Value="v2.0.0",
        Type="String",
    )


@pytest.fixture(autouse=True)
def mock_experimental_provisioned_product_per_project_limit(ssm_mock):
    ssm_mock.put_parameter(
        Name="/proserve-wb-provisioning-api/experimental-provisioned-product-per-project-limit",
        Value="3",
        Type="String",
    )


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


@pytest.fixture
def authenticated_event(cognito_user_pool_mock, mock_cognito_user):
    user_sub_attribute = [x for x in mock_cognito_user["User"]["Attributes"] if x["Name"].lower() == "sub"][0]

    def _authenticated_event(body, path, http_method, query_params=None, iam_auth=False):
        payload = {
            "resource": path,
            "path": path,
            "httpMethod": http_method,
            "headers": {
                "Accept": "application/json",
                "Authorization": "Bearer eyjjdjdjdjd",
            },
            "multiValueHeaders": {"Accept": ["application/json"]},
            "queryStringParameters": query_params,
            "multiValueQueryStringParameters": (
                {key: [val] for key, val in query_params.items()} if query_params else None
            ),
            "pathParameters": {"proxy": ""},
            "stageVariables": None,
            "requestContext": {
                "authorizer": {
                    "userName": "T00123122",
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
                    "principalOrgId": "o-xxxxxxxxxx",
                    "accessKey": "AXXXXXXXXXXXXXXXXXXXXX",
                    "cognitoAuthenticationType": "authenticated",
                    "cognitoAuthenticationProvider": f"cognito-idp.us-east-1.amazonaws.com/us-east-1_lqYSBenxm,cognito-idp.us-east-1.amazonaws.com/{cognito_user_pool_mock['UserPool']['Id']}:CognitoSignIn:{user_sub_attribute['Value']}",
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

        if iam_auth:
            payload["requestContext"].pop("authorizer")

        return payload

    return _authenticated_event


@pytest.fixture
def api_schema():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(
        current_dir,
        "..",
        "schema",
        "proserve-workbench-s2s-provisioning-api-schema.yaml",
    )
    spec_dict, base_uri = read_from_filename(schema_path)
    return spec_dict


@pytest.fixture
def mock_provisioned_product():
    def _mock_provisioned_product(provisioned_product_id, product_id, user_id):
        # Import here to avoid circular imports
        from app.provisioning.domain.model import (
            product_status,
            provisioned_product,
            provisioned_product_output,
            provisioning_parameter,
        )
        from app.provisioning.entrypoints.s2s_api.tests.test_handler import (
            TEST_COMPONENT_VERSION_DETAILS,
            TEST_OS_VERSION,
        )

        return provisioned_product.ProvisionedProduct(
            projectId="proj-12345",
            provisionedProductId=provisioned_product_id,
            provisionedProductName="vt-name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId=user_id,
            userDomains=["mock-user-domain"],
            status=product_status.ProductStatus.Running,
            statusReason=None,
            productId=product_id,
            productName="Product Name",
            technologyId="tech-12345",
            versionId="vers-1",
            versionName="vers-name",
            newVersionName="new-vers-name",
            newVersionId="new-vers-id",
            isVersionRetired=True,
            versionRetiredDate=None,
            awsAccountId="12345678912",
            accountId="0987654321",
            stage=provisioned_product.ProvisionedProductStage.QA,
            region="us-east-1",
            amiId="mock-ami-id",
            scProductId="sc-product-id",
            scProvisioningArtifactId="sc-vers-id",
            scProvisionedProductId=None,
            provisioningParameters=[provisioning_parameter.ProvisioningParameter(key="mock-param-key")],
            outputs=[
                provisioned_product_output.ProvisionedProductOutput(
                    outputKey="outputs-key",
                    outputValue="outputs-value",
                )
            ],
            sshKeyPath="test",
            userCredentialName="test2",
            experimental=True,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            createDate="2023-09-01T00:00:00+00:00",
            lastUpdateDate="2023-09-01T00:00:00+00:00",
            createdBy=user_id,
            lastUpdatedBy=user_id,
        )

    return _mock_provisioned_product


@pytest.fixture
def mocked_virtual_targets_domain_query_service(mock_provisioned_product):
    mock_service = unittest.mock.create_autospec(
        spec=provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService
    )
    mock_service.get_paginated_provisioned_products.return_value = (
        [mock_provisioned_product(f"vt-{i}", f"prod-{i}", f"user-{i}") for i in range(1, 6)],
        {"string": "NextPagingKey"},
    )
    return mock_service


@pytest.fixture
def mocked_s2s_dependencies(mocked_virtual_targets_domain_query_service):
    mock_command_bus = unittest.mock.create_autospec(spec=command_bus.CommandBus)
    mock_products_qry_srv = unittest.mock.create_autospec(spec=products_domain_query_service.ProductsDomainQueryService)
    mock_versions_qry_srv = unittest.mock.create_autospec(spec=versions_domain_query_service.VersionsDomainQueryService)

    return bootstrapper.Dependencies(
        command_bus=mock_command_bus,
        products_domain_qry_srv=mock_products_qry_srv,
        versions_domain_qry_srv=mock_versions_qry_srv,
        virtual_targets_domain_qry_srv=mocked_virtual_targets_domain_query_service,
    )
