import unittest
from unittest import mock

import boto3
import botocore
import moto
import pytest
from attr import dataclass
from moto import mock_aws

from app.provisioning.domain.model import (
    additional_configuration,
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.ports import provisioned_products_query_service

orig = botocore.client.BaseClient._make_api_call

TEST_TABLE_NAME = "TEST"
TEST_REGION = "us-east-1"


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.provisioning.entrypoints.provisioned_product_event_handlers.bootstrapper.migrations_config",
        return_value=[],
    ):
        yield


@pytest.fixture(autouse=True)
def mock_sts():
    with moto.mock_aws():
        yield boto3.client("sts", region_name=TEST_REGION)


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
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("USER_POOL_URL", "https://fake.com")
    monkeypatch.setenv("AWS_ACCOUNT", "123456789012")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Authorizer")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("APP_CONFIG_APP_NAME", "fake_app_name")
    monkeypatch.setenv("APP_CONFIG_ENV_NAME", "fake_env_name")
    monkeypatch.setenv("API_ROLE_CONFIG_NAME", "fake_param_name")
    monkeypatch.setenv("AWS_APPCONFIG_EXTENSION_POLL_INTERVAL_SECONDS", "300")
    monkeypatch.setenv("AWS_APPCONFIG_EXTENSION_POLL_TIMEOUT_MILLIS", "3000")
    monkeypatch.setenv("TABLE_NAME", TEST_TABLE_NAME)
    monkeypatch.setenv(
        "PROVISIONED_PRODUCT_CLEANUP_CONFIG",
        '{"pp-cleanup-alert": 23,"pp-cleanup": 28,"pp-experimental-cleanup-alert": 5,"pp-experimental-cleanup": 7}',
    )


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


@pytest.fixture
def generate_event():
    def _generate_event(
        cf_stack_status: str,
        cf_stack_resource: str = "AWS::CloudFormation::Stack",
    ):
        return {
            "version": "0",
            "id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "detail-type": "Catalog SNS notifications",
            "source": "Workbench Catalog Service",
            "account": "111111111111",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": ["Service Catalog"],
            "detail": {
                "Type": "Notification",
                "MessageId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "TopicArn": "arn:aws:sns:us-east-1:111111111111:Message2EventTransformerTopic",
                "Subject": "AWS CloudFormation Notification",
                "Message": f"StackId='arn:aws:cloudformation:us-east-1:111111111111:stack/SC-00000000-pp-00000000/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'\nTimestamp='2023-05-09T14:49:38.817Z'\nEventId='b9280f90-ee78-11ed-b25d-0e048620bb05'\nLogicalResourceId='SC-00000000-pp-00000000'\nNamespace='111111111111'\nPhysicalResourceId='arn:aws:cloudformation:us-east-1:111111111111:stack/SC-00000000-pp-00000000/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'\nPrincipalId='AROARRAKZGISM56GULW7J:servicecatalog'\nResourceProperties='null'\nResourceStatus='{cf_stack_status}'\nResourceStatusReason=''\nResourceType='{cf_stack_resource}'\nProductVersionId='vers-1234'\nStackName='SC-00000000-pp-00000000'\nClientRequestToken='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'\n",
                "Timestamp": "2022-11-14T17:15:50.354Z",
                "SignatureVersion": "1",
                "Signature": "----",
                "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-00000000.pem",
                "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:111111111111:Message2EventTransformerTopic:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "MessageAttributes": {},
            },
        }

    return _generate_event


@pytest.fixture(autouse=True)
def mock_moto_calls(
    mmock_search_provisioned_products,
):
    invocations = {"SearchProvisionedProducts": mmock_search_provisioned_products}

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with unittest.mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mmock_search_provisioned_products(mocked_search_provisioned_products_response):
    return unittest.mock.MagicMock(return_value=mocked_search_provisioned_products_response)


@pytest.fixture()
def mocked_search_provisioned_products_response():
    return {
        "ProvisionedProducts": [
            {
                "Name": "string",
                "Arn": "arn:aws:cloudformation:us-east-1:111111111111:stack/SC-00000000-pp-00000000/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "Type": "string",
                "Id": "pp-00000000",
                "Status": "AVAILABLE",
                "StatusMessage": "string",
                "CreatedTime": "2023-12-13",
                "IdempotencyToken": "string",
                "LastRecordId": "string",
                "LastProvisioningRecordId": "string",
                "LastSuccessfulProvisioningRecordId": "string",
                "Tags": [
                    {"Key": "vew:provisionedProduct:productType", "Value": "VIRTUAL_TARGET"},
                    {"Key": "vew:provisionedProduct:id", "Value": "pp-00000000"},
                ],
                "PhysicalId": "string",
                "ProductId": "string",
                "ProductName": "string",
                "ProvisioningArtifactId": "string",
                "ProvisioningArtifactName": "string",
                "UserArn": "string",
                "UserArnSession": "string",
            },
        ],
        "TotalResultsCount": 123,
        "NextPageToken": "string",
    }


@pytest.fixture()
def get_provisioned_product():
    def _inner(
        status: product_status.ProductStatus = product_status.ProductStatus.Provisioning,
        sc_provisioned_product_id: str | None = None,
        product_id: str = "prod-123",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        region: str = "us-east-1",
        version_id: str = "vers-123",
        provisioned_product_id: str = "pp-123",
        new_version_id: str | None = None,
        new_version_name: str | None = None,
        upgrade_available: bool | None = None,
        version_name: str = "v1.0.0",
        additional_configurations: list[additional_configuration.AdditionalConfiguration] | None = None,
    ):
        return provisioned_product.ProvisionedProduct(
            projectId="proj-123",
            provisionedProductId=provisioned_product_id,
            provisionedProductName="my name",
            provisionedProductType=provisioned_product.ProvisionedProductType.VirtualTarget,
            userId="T0011AA",
            userDomains=["domain"],
            status=status,
            productId=product_id,
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId=version_id,
            versionName=version_name,
            awsAccountId="00111111111111",
            accountId="acc-123",
            instanceId="i-0111111111111abcdef",
            stage=stage,
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value"),
                provisioning_parameter.ProvisioningParameter(key="UserSecurityGroupId"),
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            newVersionId=new_version_id,
            newVersionName=new_version_name,
            upgradeAvailable=upgrade_available,
            additionalConfigurations=additional_configurations,
        )

    return _inner


@pytest.fixture(autouse=True)
def mock_pp_qs(get_provisioned_product):
    vt_qs = mock.create_autospec(spec=provisioned_products_query_service.ProvisionedProductsQueryService)
    vt_qs.get_by_sc_provisioned_product_id.return_value = get_provisioned_product()
    return vt_qs
