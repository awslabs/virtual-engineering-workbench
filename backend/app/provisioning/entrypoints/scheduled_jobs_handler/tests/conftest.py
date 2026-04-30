import logging
from datetime import datetime
from unittest import mock

import boto3
import botocore
import moto
import pytest
from attr import dataclass

from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.domain.commands.product_provisioning import (
    cleanup_provisioned_products_command,
)
from app.provisioning.domain.commands.provisioned_product_state import (
    initiate_provisioned_product_batch_stop_command,
    sync_provisioned_product_state_command,
)
from app.provisioning.domain.model import (
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.query_services import (
    projects_domain_query_service,
    provisioned_products_domain_query_service,
)
from app.provisioning.domain.read_models import project
from app.provisioning.entrypoints.scheduled_jobs_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

TEST_TABLE_NAME = "TEST"
GSI_NAME_ENTITIES = "gsi_entities"
GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
GSI_NAME_CUSTOM_QUERY_BY_SC_ID = "gsi_custom_query_by_sc_id"
GSI_NAME_CUSTOM_QUERY_BY_USER_ID = "gsi_custom_query_by_user_id"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2 = "gsi_custom_query_by_alternative_key_2"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3 = "gsi_custom_query_by_alternative_keys_3"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4 = "gsi_custom_query_by_alternative_keys_4"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5 = "gsi_custom_query_by_alternative_keys_5"


@pytest.fixture(autouse=True)
def disable_migrations():
    with mock.patch(
        "app.provisioning.entrypoints.scheduled_jobs_handler.bootstrapper.migrations_config",
        return_value=[],
    ):
        yield


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
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT", "123456789012")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ScheduledJobEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "DOMAIN_EVENT_BUS_ARN",
        "arn:aws:events:us-east-1:001234567890:event-bus/projects-events",
    )
    monkeypatch.setenv("BOUNDED_CONTEXT", "provisioning")
    monkeypatch.setenv("PROJECTS_API_URL", "projects-api-url")
    monkeypatch.setenv("VEW_ORGANIZATION_PREFIX", "proserve")
    monkeypatch.setenv("VEW_APPLICATION_PREFIX", "wb")
    monkeypatch.setenv("APP_ENVIRONMENT", "dev")
    monkeypatch.setenv(
        "PROVISIONED_PRODUCT_CLEANUP_CONFIG",
        '{"pp-cleanup-alert": 23,"pp-cleanup": 28,"pp-experimental-cleanup-alert": 5,"pp-experimental-cleanup": 7}',
    )
    monkeypatch.setenv("TABLE_NAME", mock_table_name)
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", GSI_NAME_INVERTED_PK)
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY", GSI_NAME_CUSTOM_QUERY_BY_SC_ID)
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2", GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2)
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3", GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3)
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4", GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4)
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5", GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5)
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_USER_KEY", GSI_NAME_CUSTOM_QUERY_BY_USER_ID)


@pytest.fixture
def metric_producer_job_event():
    return {"jobName": "MetricProducerJob"}


@pytest.fixture
def provisioned_product_sync_job_event():
    return {"jobName": "ProvisionedProductSyncJob"}


@pytest.fixture
def provisioned_product_cleanup_job_event():
    return {"jobName": "ProvisionedProductCleanupJob"}


@pytest.fixture
def provisioned_product_batch_stop_job_event():
    return {"jobName": "ProvisionedProductBatchStopJob"}


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture()
def get_sample_provisioned_product():
    def _inner(
        provisioned_product_id: str = "pp-123",
        status: product_status.ProductStatus = product_status.ProductStatus.Running,
        sc_provisioned_product_id: str | None = None,
        user_id: str = "T0011AA",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        product_id: str = "prod-123",
        provisioned_product_type: provisioned_product.ProvisionedProductType = provisioned_product.ProvisionedProductType.VirtualTarget,
        project_id: str = "proj-123",
        instance_id: str | None = None,
    ):
        return provisioned_product.ProvisionedProduct(
            projectId=project_id,
            provisionedProductId=provisioned_product_id,
            provisionedProductName="my name",
            provisionedProductType=provisioned_product_type,
            userId=user_id,
            userDomains=["domain"],
            status=status,
            productId=product_id,
            productName="Pied Piper",
            productDescription="Compression",
            technologyId="tech-123",
            versionId="vers-123",
            versionName="v1.0.0",
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=stage,
            region="us-east-1",
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value")
            ],
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            startDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
            instanceId=instance_id,
        )

    return _inner


@pytest.fixture
def mock_provisioned_products_domain_query_service(get_sample_provisioned_product):
    mock_qs = mock.create_autospec(spec=provisioned_products_domain_query_service.ProvisionedProductsDomainQueryService)
    mock_qs.get_provisioned_products.side_effect = [
        [
            get_sample_provisioned_product(provisioned_product_id="pp-123"),
            get_sample_provisioned_product(provisioned_product_id="pp-234", user_id="user-2"),
            get_sample_provisioned_product(
                provisioned_product_id="pp-345",
                user_id="user-3",
                status=product_status.ProductStatus.Provisioning,
            ),
        ],
        [
            get_sample_provisioned_product(provisioned_product_id="pp-1234", project_id="proj-234"),
            get_sample_provisioned_product(
                provisioned_product_id="pp-2345",
                user_id="user-2",
                project_id="proj-234",
            ),
            get_sample_provisioned_product(
                provisioned_product_id="pp-3456",
                user_id="user-3",
                project_id="proj-234",
                status=product_status.ProductStatus.Provisioning,
            ),
        ],
    ]
    return mock_qs


@pytest.fixture
def mock_projects_domain_query_service():
    mock_qs = mock.create_autospec(spec=projects_domain_query_service.ProjectsDomainQueryService)
    mock_qs.get_projects.return_value = [
        project.Project(projectId="proj-123", projectName="Program A"),
        project.Project(projectId="proj-234", projectName="Program B"),
    ]
    return mock_qs


@pytest.fixture
def mock_sync_provisioned_products_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_provisioned_product_cleanup_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_initiate_provisioned_product_batch_stop_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_dependencies(
    mock_provisioned_product_cleanup_command_handler,
    mock_provisioned_products_domain_query_service,
    mock_projects_domain_query_service,
    mock_logger,
    mock_sync_provisioned_products_command_handler,
    mock_initiate_provisioned_product_batch_stop_command_handler,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            sync_provisioned_product_state_command.SyncProvisionedProductStateCommand,
            mock_sync_provisioned_products_command_handler,
        )
        .register_handler(
            cleanup_provisioned_products_command.CleanupProvisionedProductsCommand,
            mock_provisioned_product_cleanup_command_handler,
        )
        .register_handler(
            initiate_provisioned_product_batch_stop_command.InitiateProvisionedProductBatchStopCommand,
            mock_initiate_provisioned_product_batch_stop_command_handler,
        ),
        provisioned_products_domain_qry_srv=mock_provisioned_products_domain_query_service,
        projects_domain_query_service=mock_projects_domain_query_service,
        provisioned_product_cleanup_config='{"pp-cleanup-alert": 23,"pp-cleanup": 28,"pp-experimental-cleanup-alert": 5,"pp-experimental-cleanup": 7}',
    )


@pytest.fixture()
def backend_app_dynamodb_table(mock_dynamodb, mock_table_name):
    table = mock_dynamodb.create_table(
        TableName=mock_table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "entity", "AttributeType": "S"},
            {"AttributeName": "QPK_1", "AttributeType": "S"},
            {"AttributeName": "QPK_2", "AttributeType": "S"},
            {"AttributeName": "QPK_3", "AttributeType": "S"},
            {"AttributeName": "QPK_4", "AttributeType": "S"},
            {"AttributeName": "QSK_3", "AttributeType": "S"},
            {"AttributeName": "GSI_PK", "AttributeType": "S"},
            {"AttributeName": "GSI_SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        GlobalSecondaryIndexes=[
            {
                "IndexName": GSI_NAME_ENTITIES,
                "KeySchema": [
                    {"AttributeName": "entity", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_INVERTED_PK,
                "KeySchema": [
                    {"AttributeName": "SK", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_CUSTOM_QUERY_BY_SC_ID,
                "KeySchema": [
                    {"AttributeName": "QPK_1", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_CUSTOM_QUERY_BY_USER_ID,
                "KeySchema": [
                    {"AttributeName": "GSI_PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI_SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2,
                "KeySchema": [
                    {"AttributeName": "QPK_2", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3,
                "KeySchema": [
                    {"AttributeName": "QPK_3", "KeyType": "HASH"},
                    {"AttributeName": "QSK_3", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4,
                "KeySchema": [
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "QSK_3", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5,
                "KeySchema": [
                    {"AttributeName": "QPK_4", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
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


@pytest.fixture
def mock_sts():
    with moto.mock_aws():
        yield boto3.client("sts")


@pytest.fixture
def mock_events():
    with moto.mock_aws():
        yield boto3.client("events")


@pytest.fixture()
def mock_ddb_repo(mock_logger, mock_table_name, mock_dynamodb, backend_app_dynamodb_table):
    return dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=mock_table_name).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture
def mock_provisioned_products(mock_ddb_repo, get_sample_provisioned_product):
    with mock_ddb_repo:
        repo = mock_ddb_repo.get_repository(
            provisioned_product.ProvisionedProductPrimaryKey,
            provisioned_product.ProvisionedProduct,
        )

        repo.add(get_sample_provisioned_product(instance_id="i-123"))
        repo.add(
            get_sample_provisioned_product(
                status=product_status.ProductStatus.Stopped,
                provisioned_product_id="pp-456",
                instance_id="i-123",
            )
        )

        mock_ddb_repo.commit()


orig = botocore.client.BaseClient._make_api_call


@pytest.fixture()
def mock_moto_calls(
    mock_get_metric_data_request,
    mock_put_events_request,
):
    invocations = {
        "GetMetricData": mock_get_metric_data_request,
        "PutEvents": mock_put_events_request,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mock_get_metric_data_request():
    return mock.MagicMock(
        return_value={
            "MetricDataResults": [
                {
                    "Id": "q1",
                    "Label": "i-123 pp-123",
                    "Timestamps": [datetime.fromisoformat("2025-04-10T12:35:00+00:00")],
                    "Values": [0.0],
                    "StatusCode": "Complete",
                }
            ],
            "Messages": [],
        }
    )


@pytest.fixture()
def mock_put_events_request():
    return mock.MagicMock(return_value={"Entries": [{"EventId": "123"}], "FailedEntryCount": 0})
