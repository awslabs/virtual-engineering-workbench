import logging
from datetime import datetime
from enum import Enum
from unittest import mock

import boto3
import botocore
import moto
import pytest
from freezegun import freeze_time

from app.packaging.adapters.query_services import (
    dynamodb_component_query_service,
    dynamodb_component_version_query_service,
    dynamodb_component_version_test_execution_query_service,
    dynamodb_image_query_service,
    dynamodb_mandatory_components_list_query_service,
    dynamodb_pipeline_query_service,
    dynamodb_recipe_query_service,
    dynamodb_recipe_version_query_service,
    dynamodb_recipe_version_test_execution_query_service,
)
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.services import (
    aws_component_definition_service,
    aws_component_version_testing_service,
    aws_recipe_version_testing_service,
    ec2_image_builder_component_service,
    ec2_image_builder_pipeline_service,
    ec2_image_builder_recipe_service,
    parameter_service,
)
from app.packaging.domain.model.component import (
    component,
    component_project_association,
    component_version,
    component_version_test_execution,
    mandatory_components_list,
)
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import (
    recipe,
    recipe_version,
    recipe_version_test_execution,
)
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.model.shared.component_version_entry import (
    ComponentVersionEntry,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work


class GlobalVariables(Enum):
    TEST_PARAMETER_TYPE = "String"
    TEST_PARAMETER_VALUE = "test_value"
    TEST_PARAMETER_NAME = "/test/parameter"
    AWS_SESSION_TOKEN = "SESSION_TOKEN"
    AWS_SECURITY_TOKEN = "SECURITY_TOKEN"
    AWS_SECRET_ACCESS_KEY = "SECRET_ACCESS_KEY"
    AWS_AWS_ACCESS_KEY_ID = "ACCESS_KEY_ID"
    AWS_ACCOUNT_ID = "123456789012"
    REQUEST_ID = "req-1234567890"
    CLIENT_TOKEN = "token-1234567890"
    FAKE_BUCKET_NAME = "fake_bucket"
    FAKE_BUCKET = {"Bucket": FAKE_BUCKET_NAME}
    FAKE_BUCKET_OBJECT_KEY = {"Key": "component_definition.yaml"}
    TEST_LAST_UPDATED_BY = "T0011AA"
    TEST_CREATED_BY = "T0011AA"
    TEST_LAST_UPDATE_DATE = "2000-01-01"
    TEST_CREATE_DATE = "2000-01-01"
    TEST_ADMIN_ROLE = "admin"
    TEST_AMI_FACTORY_AWS_ACCOUNT_ID = "123456789012"
    TEST_AMI_FACTORY_VPC_NAME = "vpc-test"
    TEST_AMI_FACTORY_SUBNET_NAMES = ["subnet-1a"]
    TEST_AMI_ID = "ami-01234567890abcdef"
    TEST_ARCHITECTURE = "amd64"
    TEST_GSI_NAME_ENTITIES = "gsi_entities"
    TEST_GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN = "gsi_custom_query_by_build_version_arn"
    TEST_GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION = "gsi_custom_query_by_recipe_id_and_version"
    TEST_GSI_NAME_CUSTOM_QUERY_BY_STATUS = "gsi_custom_query_by_status_key"
    TEST_GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
    TEST_GSI_NAME_IMAGE_UPSTREAM_ID = "gsi_image_upstream_id"
    TEST_IMAGE_KEY_NAME = "test-key"
    TEST_INSTANCE_ID = "i-01234567890abcdef"
    TEST_INSTANCE_PROFILE_NAME = "instance-profile-test"
    SSM_RUN_COMMAND_TIMEOUT = 60
    TEST_INSTANCE_ROLE_NAME = "role-test"
    TEST_INSTANCE_SECURITY_GROUP_NAME = "sg-test"
    TEST_INSTANCE_TYPE = "m8i.2xlarge"
    TEST_INSTANCE_CONNECTION_STATUS = (
        component_version_test_execution.ComponentVersionTestExecutionInstanceStatus.Disconnected.value
    )
    TEST_INSTANCE_STATUS = component_version_test_execution.ComponentVersionTestExecutionStatus.Pending.value
    TEST_OS_VERSION = "Ubuntu 24"
    TEST_PLATFORM = "Linux"
    TEST_PROJECT_ID = "proj-12345"
    TEST_RECIPE_ID = "reci-1234abcd"
    TEST_RECIPE_DESCRIPTION = "Test recipe description"
    TEST_RECIPE_VERSION_ID = "vers-1234abcd"
    TEST_RECIPE_VERSION_NAME = "1.0.0"
    TEST_RECIPE_NAME = "proserve-autosar-recipe"
    TEST_RECIPE_STATUS = "CREATED"
    TEST_RECIPE_VERSION_PARENT_IMAGE_ID = "image-12345"
    TEST_RECIPE_VERSION_DESCRIPTION = "Test recipe version description"
    TEST_RECIPE_VERSION_ARN = "arn"
    TEST_RECIPE_VERSION_STATUS = "CREATED"
    TEST_RECIPE_VERSION_COMPONENTS_VERSIONS = [
        component_version_entry.ComponentVersionEntry(
            componentId="comp-12345",
            componentName="component-12345",
            componentVersionId="vers-12345",
            componentVersionName="1.0.0-rc.1",
            order=1,
        )
    ]
    TEST_RECIPE_VERSION_VOLUME_SIZE = "8"
    TEST_RECIPE_TEST_BUCKET_NAME = "test-bucket"
    TEST_COMPONENT_TEST_BUCKET_NAME = "test-bucket"
    SUPPORTED_ARCHITECTURES = ["amd64", "arm64"]
    TEST_REGION = "us-east-1"
    TEST_TABLE_NAME = "test-table"
    TEST_VOLUME_SIZE = 500
    DEFAULT_PAGE_SIZE = 50
    TEST_COMPONENT_ID = "comp-1"
    TEST_COMPONENT_NAME = "Test Component"
    TEST_COMPONENT_VERSION_ID = "version-1"
    TEST_COMPONENT_VERSION_NAME = "1.0.0"
    TEST_COMPONENT_DESCRIPTION = "Test Description"
    TEST_COMPONENT_PLATFORM = "Linux"
    TEST_COMPONENT_SUPPORTED_ARCHITECTURES = ["amd64"]
    TEST_COMPONENT_SUPPORTED_OS_VERSIONS = ["Ubuntu 24"]
    TEST_COMPONENT_BUILD_VERSION_ARN = "arn::test"
    TEST_COMPONENT_VERSION_S3_URI = f"s3://{FAKE_BUCKET_NAME}/{FAKE_BUCKET_OBJECT_KEY.get('Key')}"
    TEST_SETUP_COMMAND_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"
    TEST_SETUP_COMMAND_STATUS = "SUCCESS"
    TEST_SETUP_COMMAND_OUTPUT = "This is a test output"
    TEST_SETUP_COMMAND_ERROR = "This is a test error"
    TEST_TEST_EXECUTION_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"
    TEST_TEST_COMMAND_ID = "750ac01c-c984-4ea0-b16f-d79819930140"
    TEST_TEST_COMMAND_ERROR = "This is a test error"
    TEST_TEST_COMMAND_OUTPUT = "This is a test output"
    TEST_TEST_COMMAND_STATUS = "SUCCESS"
    TEST_IMAGE_UPSTREAM_ID = "ami-01234567890abcdef"
    TEST_IMAGE_ID = "image-12345"
    TEST_IMAGE_BUILD_VERSION = 1
    TEST_IMAGE_STATUS = "CREATING"
    TEST_IMAGE_RECIPE_ARN = (
        f"arn:aws:imagebuilder:{TEST_REGION}:{TEST_AMI_FACTORY_AWS_ACCOUNT_ID}"
        f":image-recipe/{TEST_RECIPE_ID}/{TEST_RECIPE_VERSION_NAME}"
    )
    TEST_IMAGE_BUILD_VERSION_ARN = (
        f"arn:aws:imagebuilder:{TEST_REGION}:{TEST_AMI_FACTORY_AWS_ACCOUNT_ID}"
        f":image/{TEST_RECIPE_ID}/{TEST_RECIPE_VERSION_NAME}/1"
    )
    TEST_PIPELINE_ID = "pipe-12345"
    TEST_PIPELINE_NAME = "Test pipeline"
    TEST_PIPELINE_STATUS = "CREATING"
    TEST_PIPELINE_DESCRIPTION = "Test pipeline description"
    TEST_PIPELINE_BUILD_INSTANCE_TYPES = ["m8i.2xlarge", "m8i.4xlarge"]
    TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN = (
        f"arn:aws:imagebuilder:{TEST_REGION}:{TEST_AMI_FACTORY_AWS_ACCOUNT_ID}:"
        f"distribution-configuration/{TEST_PIPELINE_ID}"
    )
    TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN = (
        f"arn:aws:imagebuilder:{TEST_REGION}:{TEST_AMI_FACTORY_AWS_ACCOUNT_ID}:"
        f"infrastructure-configuration/{TEST_PIPELINE_ID}"
    )
    TEST_PIPELINE_ARN = (
        f"arn:aws:imagebuilder:{TEST_REGION}:{TEST_AMI_FACTORY_AWS_ACCOUNT_ID}:image-pipeline/{TEST_PIPELINE_ID}"
    )
    TEST_PIPELINE_SCHEDULE = "0 10 * * ? *"
    TEST_TOPIC_NAME = "topic-test"
    TEST_PIPELINE_SNS_TOPIC_ARN = f"arn:aws:sns:{TEST_REGION}:{TEST_AMI_FACTORY_AWS_ACCOUNT_ID}:{TEST_TOPIC_NAME}"
    TEST_TEST_INSTANCE_ID = "i-123456789"
    DDB_SIMPLE_TABLE_DEFINITION = {
        "TableName": TEST_TABLE_NAME,
        "KeySchema": [
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI_PK", "AttributeType": "S"},
            {"AttributeName": "GSI_SK", "AttributeType": "S"},
            {"AttributeName": "QPK_ARN", "AttributeType": "S"},
            {"AttributeName": "QPK_RECIPE", "AttributeType": "S"},
            {"AttributeName": "QSK_VERSION", "AttributeType": "S"},
            {"AttributeName": "entity", "AttributeType": "S"},
            {"AttributeName": "imageUpstreamId", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "gsi_custom_query_by_build_version_arn",
                "KeySchema": [
                    {"AttributeName": "QPK_ARN", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "gsi_custom_query_by_recipe_id_and_version",
                "KeySchema": [
                    {"AttributeName": "QPK_RECIPE", "KeyType": "HASH"},
                    {"AttributeName": "QSK_VERSION", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "gsi_custom_query_by_status_key",
                "KeySchema": [
                    {"AttributeName": "GSI_PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI_SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "gsi_entities",
                "KeySchema": [
                    {"AttributeName": "entity", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": "gsi_inverted_primary_key",
                "KeySchema": [
                    {"AttributeName": "SK", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
            {
                "IndexName": TEST_GSI_NAME_IMAGE_UPSTREAM_ID,
                "KeySchema": [
                    {"AttributeName": "imageUpstreamId", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
        ],
    }
    TEST_COMPONENT_SOFTWARE_VENDOR = "vector"
    TEST_COMPONENT_SOFTWARE_VERSION = "1.0.0"
    TEST_COMPONENT_LICENSE_DASHBOARD_URL = "https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1"
    TEST_COMPONENT_SOFTWARE_VERSION_NOTES = "This is a test component version note."
    TEST_COMPONENT_VERSION_YAML_DEFINITION = "Name: Test component"


orig = botocore.client.BaseClient._make_api_call


def backend_app_dynamodb_dynamic_table(mock_dynamodb, ddb_table_definition: dict, table_name: str):
    table = mock_dynamodb.create_table(**ddb_table_definition)

    table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
    return table


@pytest.fixture()
def backend_app_table(mock_dynamodb):
    return backend_app_dynamodb_dynamic_table(
        mock_dynamodb=mock_dynamodb,
        ddb_table_definition=dict(GlobalVariables.DDB_SIMPLE_TABLE_DEFINITION.value),
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
    )


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture()
def uow_mock(mock_dynamodb, mock_logger):
    return dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(
            table_name=GlobalVariables.TEST_TABLE_NAME.value
        ).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture(autouse=True)
def mock_iam_client():
    with moto.mock_aws():
        yield boto3.client("iam", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture(autouse=True)
def mock_s3_client():
    with moto.mock_aws():
        yield boto3.client("s3", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture(autouse=True)
def mock_s3_bucket(mock_s3_client):
    mock_s3_client.create_bucket(**dict(GlobalVariables.FAKE_BUCKET.value))


@pytest.fixture(autouse=True)
def mock_s3_yaml_file(mock_s3_client):
    mock_s3_client.put_object(
        **dict(GlobalVariables.FAKE_BUCKET.value),
        **dict(GlobalVariables.FAKE_BUCKET_OBJECT_KEY.value),
        Body=GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value.encode("utf-8"),
    )


@pytest.fixture(autouse=True)
def mock_ssm_client():
    with moto.mock_aws():
        yield boto3.client("ssm", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture(autouse=True)
def mock_sts():
    with moto.mock_aws():
        yield boto3.client("sts", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture
def mock_dynamodb():
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture()
def mock_ec2_client():
    with moto.mock_aws():
        yield boto3.client("ec2", region_name=GlobalVariables.TEST_REGION.value)


def mock_ddb_dynamic_repo(mock_logger, mock_dynamodb, table_name: str = None):
    return dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=table_name).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture()
def mock_ddb_component_repo(mock_dynamodb, mock_logger):
    return mock_ddb_dynamic_repo(
        mock_dynamodb=mock_dynamodb,
        mock_logger=mock_logger,
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
    )


@pytest.fixture()
def mock_moto_calls(
    mock_create_component_response,
    mock_delete_component_response,
    mock_delete_recipe_response,
    mock_get_command_invocation,
    mock_get_connection_status,
    mock_list_components_response,
    mock_create_recipe_response,
    mock_get_recipe_response,
    mock_create_distribution_config_response,
    mock_create_infrastructure_config_response,
    mock_create_pipeline_response,
    mock_delete_distribution_config_response,
    mock_delete_infrastructure_config_response,
    mock_delete_pipeline_response,
    mock_list_image_pipeline_images,
    mock_start_pipeline_execution_response,
    mock_update_distribution_config_response,
    mock_update_infrastructure_config_response,
    mock_update_pipeline_response,
):
    create_component = "CreateComponent"
    delete_component = "DeleteComponent"
    delete_recipe = "DeleteImageRecipe"
    get_command_invocation = "GetCommandInvocation"
    get_connection_status = "GetConnectionStatus"
    list_components = "ListComponents"
    create_recipe = "CreateImageRecipe"
    get_recipe = "ListImageRecipes"
    create_distribution_config = "CreateDistributionConfiguration"
    create_infrastructure_config = "CreateInfrastructureConfiguration"
    create_pipeline = "CreateImagePipeline"
    delete_distribution_config = "DeleteDistributionConfiguration"
    delete_infrastructure_config = "DeleteInfrastructureConfiguration"
    delete_pipeline = "DeleteImagePipeline"
    list_image_pipeline_images = "ListImagePipelineImages"
    start_pipeline_execution = "StartImagePipelineExecution"
    update_distribution_config = "UpdateDistributionConfiguration"
    update_infrastructure_config = "UpdateInfrastructureConfiguration"
    update_pipeline = "UpdateImagePipeline"

    invocations = {
        create_component: mock.MagicMock(return_value=mock_create_component_response),
        delete_component: mock.MagicMock(return_value=mock_delete_component_response),
        delete_recipe: mock.MagicMock(return_value=mock_delete_recipe_response),
        get_command_invocation: mock.MagicMock(return_value=mock_get_command_invocation),
        get_connection_status: mock.MagicMock(return_value=mock_get_connection_status),
        list_components: mock.MagicMock(return_value=mock_list_components_response),
        create_recipe: mock.MagicMock(return_value=mock_create_recipe_response),
        get_recipe: mock.MagicMock(return_value=mock_get_recipe_response),
        create_distribution_config: mock.MagicMock(return_value=mock_create_distribution_config_response),
        create_infrastructure_config: mock.MagicMock(return_value=mock_create_infrastructure_config_response),
        create_pipeline: mock.MagicMock(return_value=mock_create_pipeline_response),
        delete_distribution_config: mock.MagicMock(return_value=mock_delete_distribution_config_response),
        delete_infrastructure_config: mock.MagicMock(return_value=mock_delete_infrastructure_config_response),
        delete_pipeline: mock.MagicMock(return_value=mock_delete_pipeline_response),
        list_image_pipeline_images: mock.MagicMock(return_value=mock_list_image_pipeline_images),
        start_pipeline_execution: mock.MagicMock(return_value=mock_start_pipeline_execution_response),
        update_distribution_config: mock.MagicMock(return_value=mock_update_distribution_config_response),
        update_infrastructure_config: mock.MagicMock(return_value=mock_update_infrastructure_config_response),
        update_pipeline: mock.MagicMock(return_value=mock_update_pipeline_response),
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mock_moto_ec2_calls(
    mock_ec2_launch_instances_call,
):
    invocations = {
        "RunInstances": mock_ec2_launch_instances_call,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mock_ec2_launch_instances_call():
    return mock.MagicMock(return_value={"Instances": [{"InstanceId": "i-0000000000"}]})


@pytest.fixture()
def get_test_component_version_object_without_s3_uri():
    return component_version.ComponentVersion(
        componentId=GlobalVariables.TEST_COMPONENT_ID.value,
        componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
        componentName="test-component",
        componentVersionDescription="Test description",
        componentBuildVersionArn="arn::test",
        componentPlatform="Linux",
        componentSupportedArchitectures=["arm64"],
        componentSupportedOsVersions=["Ubuntu 24"],
        status=component_version.ComponentVersionStatus.Created,
        createDate="2023-10-27T00:00:00+00:00",
        createdBy="T000001",
        lastUpdateDate="2023-10-27T00:00:00+00:00",
        lastUpdatedBy="T000001",
    )


@pytest.fixture
def mock_create_component_response():
    return {
        "requestId": GlobalVariables.REQUEST_ID.value,
        "clientToken": GlobalVariables.CLIENT_TOKEN.value,
        "componentBuildVersionArn": f"arn:aws:imagebuilder:us-east-1:1234567890:component/{GlobalVariables.TEST_COMPONENT_ID.value}/{GlobalVariables.TEST_COMPONENT_VERSION_NAME.value}",
    }


@pytest.fixture
def mock_delete_component_response():
    return {
        "requestId": GlobalVariables.REQUEST_ID.value,
        "componentBuildVersionArn": f"arn:aws:imagebuilder:us-east-1:1234567890:component/{GlobalVariables.TEST_COMPONENT_ID.value}/{GlobalVariables.TEST_COMPONENT_VERSION_NAME.value}/1",
    }


@pytest.fixture
def mock_delete_recipe_response():
    return {
        "requestId": GlobalVariables.REQUEST_ID.value,
        "imageRecipeArn": f"arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/{GlobalVariables.TEST_RECIPE_ID.value}/{GlobalVariables.TEST_RECIPE_VERSION_NAME.value}",
    }


@pytest.fixture
def mock_create_recipe_response():
    return {
        "requestId": GlobalVariables.REQUEST_ID.value,
        "imageRecipeArn": f"arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/{GlobalVariables.TEST_RECIPE_ID.value}/{GlobalVariables.TEST_RECIPE_VERSION_NAME.value}",
    }


@pytest.fixture
def mock_get_recipe_response():
    return {
        "requestId": GlobalVariables.REQUEST_ID.value,
        "imageRecipeSummaryList": [
            {
                "arn": f"arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/{GlobalVariables.TEST_RECIPE_ID.value}/{GlobalVariables.TEST_RECIPE_VERSION_NAME.value}",
                "name": GlobalVariables.TEST_RECIPE_NAME.value,
                "platform": "Linux",
                "owner": "1234567890",
                "parentImage": GlobalVariables.TEST_RECIPE_VERSION_PARENT_IMAGE_ID.value,
                "dateCreated": datetime(2024, 1, 17),
                "tags": {"name": "test-recipe"},
            },
        ],
    }


@pytest.fixture
def mock_get_command_invocation():
    return {
        "CommandId": GlobalVariables.TEST_TEST_COMMAND_ID.value,
        "InstanceId": GlobalVariables.TEST_TEST_INSTANCE_ID.value,
        "Comment": "string",
        "DocumentName": "string",
        "DocumentVersion": "string",
        "PluginName": "string",
        "ResponseCode": 0,
        "ExecutionStartDateTime": "string",
        "ExecutionElapsedTime": "string",
        "ExecutionEndDateTime": "string",
        "Status": "Success",
        "StatusDetails": "string",
        "StandardOutputContent": "This is an example output",
        "StandardOutputUrl": "string",
        "StandardErrorContent": "This is an example error",
        "StandardErrorUrl": "string",
        "CloudWatchOutputConfig": {
            "CloudWatchLogGroupName": "string",
            "CloudWatchOutputEnabled": True,
        },
    }


@pytest.fixture
def mock_get_connection_status():
    return {
        "Target": "string",
        "Status": "connected",
    }


@pytest.fixture
def mock_list_components_response():
    return {
        "componentVersionList": [
            {
                "arn": f"arn:aws:imagebuilder:us-east-1:1234567890:component/{GlobalVariables.TEST_COMPONENT_ID.value}/{GlobalVariables.TEST_COMPONENT_VERSION_NAME.value}",
                "name": GlobalVariables.TEST_COMPONENT_ID.value,
                "version": "1.0.0/1",
                "description": "Component description",
                "platform": "Linux",
                "supportedOsVersions": ["Ubuntu 24"],
                "type": "BUILD",
                "owner": "1234567890",
                "dateCreated": datetime(2023, 10, 17),
            },
        ]
    }


@pytest.fixture()
def mock_recipe_version_object(
    mock_recipe_object,
) -> recipe_version.RecipeVersion:
    return recipe_version.RecipeVersion(
        recipeId=mock_recipe_object.recipeId,
        recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
        recipeVersionDescription=GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
        recipeComponentsVersions=[
            component_version_entry.ComponentVersionEntry(
                componentId="comp-1234abc",
                componentName="component-1234abc",
                componentVersionId="vers-1234abc",
                componentVersionName="component_version-1234abc",
                order=1,
            )
        ],
        recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
        recipeVersionVolumeSize=GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
        status=recipe_version.RecipeVersionStatus.Creating,
        parentImageUpstreamId=GlobalVariables.TEST_RECIPE_VERSION_PARENT_IMAGE_ID.value,
        createDate=GlobalVariables.TEST_CREATE_DATE.value,
        createdBy=GlobalVariables.TEST_CREATED_BY.value,
        lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATED_BY.value,
    )


@pytest.fixture()
def mock_system_configuration_mapping():
    return {
        GlobalVariables.TEST_PLATFORM.value: {
            GlobalVariables.TEST_ARCHITECTURE.value: {
                GlobalVariables.TEST_OS_VERSION.value: {
                    # Adding /test/ prefix since /aws/service/ is reserved and can't be mocked
                    "ami_ssm_param_name": "/test/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id",
                    "command_ssm_document_name": "AWS-RunShellScript",
                    "instance_type": "m8i.2xlarge",
                    "run_testing_command": "awstoe run --documents << documents >> --execution-id /<< instance_id >> --log-s3-bucket-name << log_s3_bucket_name >> --log-s3-key-prefix << object_id >>/<< version_id >> --trace",
                    "setup_testing_environment_command": "curl https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/amd64/awstoe --output /usr/bin/awstoe && chmod +x /usr/bin/awstoe",
                }
            }
        },
    }


@pytest.fixture()
def mock_pipelines_configuration_mapping():
    return {
        "Pipelines": {
            "amd64": {
                "allowed_build_instance_types": [
                    "m8a.2xlarge",
                    "m8i.2xlarge",
                    "m8a.4xlarge",
                    "m8i.4xlarge",
                ]
            },
            "arm64": {"allowed_build_instance_types": ["m8g.2xlarge", "m8g.4xlarge"]},
        }
    }


@pytest.fixture()
def mock_create_distribution_config_response():
    return {"distributionConfigurationArn": GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value}


@pytest.fixture()
def mock_create_infrastructure_config_response():
    return {
        "infrastructureConfigurationArn": GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
    }


@pytest.fixture()
def mock_create_pipeline_response():
    return {"imagePipelineArn": GlobalVariables.TEST_PIPELINE_ARN.value}


@pytest.fixture()
def mock_delete_distribution_config_response():
    return {"distributionConfigurationArn": GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value}


@pytest.fixture()
def mock_delete_infrastructure_config_response():
    return {"infrastructureConfigurationArn": GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value}


@pytest.fixture()
def mock_delete_pipeline_response():
    return {"imagePipelineArn": GlobalVariables.TEST_PIPELINE_ARN.value}


@pytest.fixture()
def mock_list_image_pipeline_images():
    return {"imageSummaryList": []}


@pytest.fixture()
def mock_start_pipeline_execution_response():
    return {
        "imageBuildVersionArn": (
            f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
            f"{GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value}:"
            f"image/{GlobalVariables.TEST_RECIPE_NAME.value}/"
            f"{GlobalVariables.TEST_RECIPE_VERSION_NAME.value}/1"
        ),
    }


@pytest.fixture()
def mock_update_distribution_config_response():
    return {"distributionConfigurationArn": GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value}


@pytest.fixture()
def mock_update_infrastructure_config_response():
    return {"infrastructureConfigurationArn": GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value}


@pytest.fixture()
def mock_update_pipeline_response():
    return {"imagePipelineArn": GlobalVariables.TEST_PIPELINE_ARN.value}


@pytest.fixture()
def mock_vpc(
    mock_ec2_client,
):
    return mock_ec2_client.create_vpc(
        CidrBlock="10.0.0.0/16",
        TagSpecifications=[
            {
                "ResourceType": "vpc",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": GlobalVariables.TEST_AMI_FACTORY_VPC_NAME.value,
                    }
                ],
            }
        ],
    )


@pytest.fixture()
def mock_instance_profile(mock_iam_client):
    mock_iam_client.create_role(
        AssumeRolePolicyDocument='{"Version": "2012-10-17","Statement": [{"Effect": "Allow","Principal": {"Service": "ec2.amazonaws.com"},"Action": "sts:AssumeRole"}]}',
        RoleName=GlobalVariables.TEST_INSTANCE_ROLE_NAME.value,
    )

    mock_iam_client.create_instance_profile(
        InstanceProfileName=GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value,
    )
    mock_iam_client.add_role_to_instance_profile(
        InstanceProfileName=GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value,
        RoleName=GlobalVariables.TEST_INSTANCE_ROLE_NAME.value,
    )


@pytest.fixture()
@freeze_time("2023-10-13T00:00:00+00:00")
def mock_subnets(mock_ec2_client, mock_vpc):
    return mock_ec2_client.create_subnet(
        CidrBlock="10.0.1.0/24",
        VpcId=mock_vpc.get("Vpc").get("VpcId"),
        TagSpecifications=[
            {
                "ResourceType": "subnet",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value[0],
                    }
                ],
            }
        ],
    )


@pytest.fixture()
def mock_security_group(
    mock_ec2_client,
    mock_vpc,
):
    return mock_ec2_client.create_security_group(
        Description="test",
        GroupName=GlobalVariables.TEST_INSTANCE_SECURITY_GROUP_NAME.value,
        VpcId=mock_vpc.get("Vpc").get("VpcId"),
    )


@pytest.fixture()
@freeze_time("2023-10-13T00:00:00+00:00")
def mock_ec2_instance(
    mock_ec2_client,
    mock_subnets,
    mock_security_group,
    mock_instance_profile,
):
    return mock_ec2_client.run_instances(
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/sda1",
                "Ebs": {
                    "DeleteOnTermination": True,
                    "Encrypted": True,
                    "Iops": 3000,
                    "VolumeSize": GlobalVariables.TEST_VOLUME_SIZE.value,
                    "VolumeType": "gp3",
                },
            },
        ],
        IamInstanceProfile={"Name": GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value},
        ImageId=GlobalVariables.TEST_AMI_ID.value,
        InstanceType=GlobalVariables.TEST_INSTANCE_TYPE.value,
        MaxCount=1,
        MetadataOptions={"HttpTokens": "required"},
        MinCount=1,
        SecurityGroupIds=[mock_security_group.get("GroupId")],
        SubnetId=mock_subnets.get("Subnet").get("SubnetId"),
    )


@pytest.fixture()
def create_vpc(
    mock_ec2_client,
):
    mock_ec2_client.create_vpc(
        CidrBlock="10.0.0.0/16",
        TagSpecifications=[
            {
                "ResourceType": "vpc",
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": GlobalVariables.TEST_AMI_FACTORY_VPC_NAME.value,
                    }
                ],
            }
        ],
    )


@pytest.fixture()
def get_dynamodb_component_version_query_service(mock_dynamodb):
    return dynamodb_component_version_query_service.DynamoDBComponentVersionQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        gsi_custom_query_by_status=GlobalVariables.TEST_GSI_NAME_CUSTOM_QUERY_BY_STATUS.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture()
def get_mandatory_components_query_service(mock_dynamodb):
    return dynamodb_mandatory_components_list_query_service.DynamoDBMandatoryComponentsListQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture()
def get_dynamodb_recipe_version_query_service(
    mock_dynamodb,
):
    return dynamodb_recipe_version_query_service.DynamoDBRecipeVersionQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        gsi_custom_query_by_status=GlobalVariables.TEST_GSI_NAME_CUSTOM_QUERY_BY_STATUS.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture()
def get_dynamodb_pipeline_query_service(
    mock_dynamodb,
):
    return dynamodb_pipeline_query_service.DynamoDBPipelineQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=GlobalVariables.TEST_GSI_NAME_INVERTED_PK.value,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture()
def get_recipe_query_service(
    mock_dynamodb,
):
    return dynamodb_recipe_query_service.DynamoDBRecipeQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture()
def get_recipe_version_test_execution_query_service(
    mock_dynamodb,
):
    return dynamodb_recipe_version_test_execution_query_service.DynamoDBRecipeVersionTestExecutionQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture()
def get_dynamodb_image_query_service(
    mock_dynamodb,
):
    return dynamodb_image_query_service.DynamoDBImageQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_custom_query_by_build_version_arn=GlobalVariables.TEST_GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN.value,
        gsi_custom_query_by_recipe_id_and_version=GlobalVariables.TEST_GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION.value,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        gsi_name_image_upstream_id=GlobalVariables.TEST_GSI_NAME_IMAGE_UPSTREAM_ID.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture()
def get_dynamodb_component_query_service(
    mock_dynamodb,
):
    return dynamodb_component_query_service.DynamoDBComponentQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_inverted_primary_key=GlobalVariables.TEST_GSI_NAME_INVERTED_PK.value,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture
def get_dynamodb_component_version_test_execution_query_service(
    mock_dynamodb,
):
    return dynamodb_component_version_test_execution_query_service.DynamoDBComponentVersionTestExecutionQueryService(
        table_name=GlobalVariables.TEST_TABLE_NAME.value,
        dynamodb_client=mock_dynamodb.meta.client,
        gsi_name_entities=GlobalVariables.TEST_GSI_NAME_ENTITIES.value,
        default_page_size=int(GlobalVariables.DEFAULT_PAGE_SIZE.value),
    )


@pytest.fixture
def get_test_project_component_association():
    def _get_test_project_component_association(
        component_id: str = GlobalVariables.TEST_COMPONENT_ID.value,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        return component_project_association.ComponentProjectAssociation(
            componentId=component_id,
            projectId=project_id,
        )

    return _get_test_project_component_association


@pytest.fixture()
def get_test_component():
    def _get_test_component(
        component_id: str = GlobalVariables.TEST_COMPONENT_ID.value,
        component_description: str = GlobalVariables.TEST_COMPONENT_DESCRIPTION.value,
        component_name: str = GlobalVariables.TEST_COMPONENT_NAME.value,
        component_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        component_supported_architectures: list[str] = list(
            GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value
        ),
        component_supported_os_versions: list[str] = list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
        status: component.ComponentStatus = component.ComponentStatus.Created,
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        created_by: str = GlobalVariables.TEST_CREATED_BY.value,
        last_updated_by: str = GlobalVariables.TEST_LAST_UPDATED_BY.value,
    ):
        return component.Component(
            componentId=component_id,
            componentDescription=component_description,
            componentName=component_name,
            componentPlatform=component_platform,
            componentSupportedArchitectures=component_supported_architectures,
            componentSupportedOsVersions=component_supported_os_versions,
            status=status,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            createdBy=created_by,
            lastUpdatedBy=last_updated_by,
        )

    return _get_test_component


@pytest.fixture()
def get_component_project_association():
    def _get_component_project_association(
        component_id: str = GlobalVariables.TEST_COMPONENT_ID.value,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        return component_project_association.ComponentProjectAssociation(
            componentId=component_id,
            projectId=project_id,
        )

    return _get_component_project_association


@pytest.fixture()
def get_mock_component_version():
    def _get_mock_component_version(
        component_id: str = GlobalVariables.TEST_COMPONENT_ID.value,
        component_version_id: str = GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        component_version_name: str = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
        component_name: str = GlobalVariables.TEST_COMPONENT_NAME.value,
        component_version_description: str = GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
        component_build_version_arn: str = GlobalVariables.TEST_COMPONENT_BUILD_VERSION_ARN.value,
        component_version_s3_uri: str = GlobalVariables.TEST_COMPONENT_VERSION_S3_URI.value,
        component_platform: str = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
        component_supported_architectures: list[str] = list(
            GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value
        ),
        component_supported_os_versions: list[str] = list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
        softwareVendor: str = GlobalVariables.TEST_COMPONENT_SOFTWARE_VENDOR.value,
        softwareVersion: str = GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION.value,
        licenseDashboard: str = GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD_URL.value,
        notes: str = GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value,
        status: component_version.ComponentVersionStatus = component_version.ComponentVersionStatus.Created,
        create_date: str = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
        created_by: str = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
        last_update_date: str = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
        last_updated_by: str = GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
    ):
        return component_version.ComponentVersion(
            componentId=component_id,
            componentVersionId=component_version_id,
            componentVersionName=component_version_name,
            componentName=component_name,
            componentVersionDescription=component_version_description,
            componentBuildVersionArn=component_build_version_arn,
            componentVersionS3Uri=component_version_s3_uri,
            componentPlatform=component_platform,
            componentSupportedArchitectures=component_supported_architectures,
            componentSupportedOsVersions=component_supported_os_versions,
            softwareVendor=softwareVendor,
            softwareVersion=softwareVersion,
            licenseDashboard=licenseDashboard,
            notes=notes,
            status=status,
            createDate=create_date,
            createdBy=created_by,
            lastUpdateDate=last_update_date,
            lastUpdatedBy=last_updated_by,
        )

    return _get_mock_component_version


@pytest.fixture
def get_mock_project_component_association():
    def _get_mock_project_component_association(
        component_id: str = GlobalVariables.TEST_COMPONENT_ID.value,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        return component_project_association.ComponentProjectAssociation(
            componentId=component_id,
            projectId=project_id,
        )

    return _get_mock_project_component_association


@pytest.fixture()
def get_mock_component_version_test_execution():
    def _get_mock_component_version_test_execution(
        component_version_id: str = GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
        test_execution_id: str = GlobalVariables.TEST_TEST_EXECUTION_ID.value,
        instance_id: str = GlobalVariables.TEST_INSTANCE_ID.value,
        instance_architecture: str = GlobalVariables.TEST_ARCHITECTURE.value,
        instance_image_upstream_id: str = GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
        instance_os_version: str = GlobalVariables.TEST_OS_VERSION.value,
        instance_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        instance_status: str = GlobalVariables.TEST_INSTANCE_CONNECTION_STATUS.value,
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        status: str = GlobalVariables.TEST_INSTANCE_STATUS.value,
    ):
        return component_version_test_execution.ComponentVersionTestExecution(
            componentVersionId=component_version_id,
            testExecutionId=test_execution_id,
            instanceId=instance_id,
            instanceArchitecture=instance_architecture,
            instanceImageUpstreamId=instance_image_upstream_id,
            instanceOsVersion=instance_os_version,
            instancePlatform=instance_platform,
            instanceStatus=instance_status,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            status=status,
        )

    return _get_mock_component_version_test_execution


@pytest.fixture()
def get_mock_recipe():
    def _get_mock_recipe(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_id: str = GlobalVariables.TEST_RECIPE_ID.value,
        recipe_name: str = GlobalVariables.TEST_RECIPE_NAME.value,
        recipe_description: str = GlobalVariables.TEST_RECIPE_DESCRIPTION.value,
        recipe_platform: str = GlobalVariables.TEST_PLATFORM.value,
        recipe_architecture: str = GlobalVariables.TEST_ARCHITECTURE.value,
        recipe_os_version: str = GlobalVariables.TEST_OS_VERSION.value,
        status: str = GlobalVariables.TEST_RECIPE_STATUS.value,
        created_by: str = GlobalVariables.TEST_CREATED_BY.value,
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_updated_by: str = GlobalVariables.TEST_LAST_UPDATED_BY.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
    ):
        return recipe.Recipe(
            projectId=project_id,
            recipeId=recipe_id,
            recipeName=recipe_name,
            recipeDescription=recipe_description,
            recipePlatform=recipe_platform,
            recipeArchitecture=recipe_architecture,
            recipeOsVersion=recipe_os_version,
            status=status,
            createdBy=created_by,
            createDate=create_date,
            lastUpdatedBy=last_updated_by,
            lastUpdateDate=last_update_date,
        )

    return _get_mock_recipe


@pytest.fixture()
def get_mock_recipe_version():
    def _get_mock_recipe_version(
        recipe_id: str = GlobalVariables.TEST_RECIPE_ID.value,
        recipe_version_id: str = GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipe_version_name: str = GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
        recipe_name: str = GlobalVariables.TEST_RECIPE_NAME.value,
        recipe_version_description: str = GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
        recipe_components_versions: str = GlobalVariables.TEST_RECIPE_VERSION_COMPONENTS_VERSIONS.value,
        recipe_version_volume_size: str = GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
        status: str = GlobalVariables.TEST_RECIPE_VERSION_STATUS.value,
        parent_image_upstream_id: str = GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
        parent_image_id: str = GlobalVariables.TEST_RECIPE_VERSION_PARENT_IMAGE_ID.value,
        recipe_version_arn: str = GlobalVariables.TEST_RECIPE_VERSION_ARN.value,
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        created_by: str = GlobalVariables.TEST_CREATED_BY.value,
        last_updated_by: str = GlobalVariables.TEST_LAST_UPDATED_BY.value,
    ):
        return recipe_version.RecipeVersion(
            recipeId=recipe_id,
            recipeVersionId=recipe_version_id,
            recipeVersionName=recipe_version_name,
            recipeName=recipe_name,
            recipeVersionDescription=recipe_version_description,
            recipeComponentsVersions=recipe_components_versions,
            recipeVersionVolumeSize=recipe_version_volume_size,
            status=status,
            parentImageUpstreamId=parent_image_upstream_id,
            parentImageId=parent_image_id,
            recipeVersionArn=recipe_version_arn,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            createdBy=created_by,
            lastUpdatedBy=last_updated_by,
        )

    return _get_mock_recipe_version


@pytest.fixture()
def get_mock_image():
    def _get_mock_image(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        image_id: str = GlobalVariables.TEST_IMAGE_ID.value,
        image_build_version: int = GlobalVariables.TEST_IMAGE_BUILD_VERSION.value,
        image_build_version_arn: str = GlobalVariables.TEST_IMAGE_BUILD_VERSION_ARN.value,
        pipeline_id: str = GlobalVariables.TEST_PIPELINE_ID.value,
        pipeline_name: str = GlobalVariables.TEST_PIPELINE_NAME.value,
        recipe_id: str = GlobalVariables.TEST_RECIPE_ID.value,
        recipe_name: str = GlobalVariables.TEST_RECIPE_NAME.value,
        recipe_version_id: str = GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipe_version_name: str = GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
        status: str = GlobalVariables.TEST_IMAGE_STATUS.value,
        image_upstream_id: str = GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
    ):
        return image.Image(
            projectId=project_id,
            imageId=image_id,
            imageBuildVersion=image_build_version,
            imageBuildVersionArn=image_build_version_arn,
            pipelineId=pipeline_id,
            pipelineName=pipeline_name,
            recipeId=recipe_id,
            recipeName=recipe_name,
            recipeVersionId=recipe_version_id,
            recipeVersionName=recipe_version_name,
            status=status,
            imageUpstreamId=image_upstream_id,
            createDate=create_date,
            lastUpdateDate=last_update_date,
        )

    return _get_mock_image


@pytest.fixture()
def get_mock_recipe_version_test_execution():
    def _get_mock_recipe_version_test_execution(
        recipe_version_id: str = GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        test_execution_id: str = GlobalVariables.TEST_TEST_EXECUTION_ID.value,
        instance_id: str = GlobalVariables.TEST_INSTANCE_ID.value,
        instance_architecture: str = GlobalVariables.TEST_ARCHITECTURE.value,
        instance_os_version: str = GlobalVariables.TEST_OS_VERSION.value,
        instance_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        instance_status: str = GlobalVariables.TEST_INSTANCE_CONNECTION_STATUS.value,
        instance_image_update_id: str = GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
        setup_command_error: str = GlobalVariables.TEST_SETUP_COMMAND_ERROR.value,
        setup_command_id: str = GlobalVariables.TEST_SETUP_COMMAND_ID.value,
        setup_command_output: str = GlobalVariables.TEST_SETUP_COMMAND_OUTPUT.value,
        setup_command_status: str = GlobalVariables.TEST_SETUP_COMMAND_STATUS.value,
        test_command_error: str = GlobalVariables.TEST_TEST_COMMAND_ERROR.value,
        test_command_id: str = GlobalVariables.TEST_TEST_COMMAND_ID.value,
        test_command_output: str = GlobalVariables.TEST_TEST_COMMAND_OUTPUT.value,
        test_command_status: str = GlobalVariables.TEST_TEST_COMMAND_STATUS.value,
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        status: str = GlobalVariables.TEST_INSTANCE_STATUS.value,
    ):
        return recipe_version_test_execution.RecipeVersionTestExecution(
            recipeVersionId=recipe_version_id,
            testExecutionId=test_execution_id,
            instanceId=instance_id,
            instanceArchitecture=instance_architecture,
            instanceOsVersion=instance_os_version,
            instancePlatform=instance_platform,
            instanceStatus=instance_status,
            instanceImageUpstreamId=instance_image_update_id,
            setupCommandError=setup_command_error,
            setupCommandId=setup_command_id,
            setupCommandOutput=setup_command_output,
            setupCommandStatus=setup_command_status,
            testCommandError=test_command_error,
            testCommandId=test_command_id,
            testCommandOutput=test_command_output,
            testCommandStatus=test_command_status,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            status=status,
        )

    return _get_mock_recipe_version_test_execution


@pytest.fixture()
def get_mock_pipeline():
    def _get_mock_pipeline(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        pipeline_id: str = GlobalVariables.TEST_PIPELINE_ID.value,
        build_instance_types: list[str] = list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value),
        pipeline_description: str = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value,
        pipeline_name: str = GlobalVariables.TEST_PIPELINE_NAME.value,
        pipeline_schedule: str = GlobalVariables.TEST_PIPELINE_SCHEDULE.value,
        recipe_id: str = GlobalVariables.TEST_RECIPE_ID.value,
        recipe_name: str = GlobalVariables.TEST_RECIPE_NAME.value,
        recipe_version_id: str = GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipe_version_name: str = GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
        status: str = GlobalVariables.TEST_PIPELINE_STATUS.value,
        distribution_config_arn: str = GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        infrastructure_config_arn: str = GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        pipeline_arn: str = GlobalVariables.TEST_PIPELINE_ARN.value,
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        created_by: str = GlobalVariables.TEST_CREATED_BY.value,
        last_updated_by: str = GlobalVariables.TEST_LAST_UPDATED_BY.value,
    ):
        return pipeline.Pipeline(
            projectId=project_id,
            pipelineId=pipeline_id,
            buildInstanceTypes=build_instance_types,
            pipelineDescription=pipeline_description,
            pipelineName=pipeline_name,
            pipelineSchedule=pipeline_schedule,
            recipeId=recipe_id,
            recipeName=recipe_name,
            recipeVersionId=recipe_version_id,
            recipeVersionName=recipe_version_name,
            status=status,
            distributionConfigArn=distribution_config_arn,
            infrastructureConfigArn=infrastructure_config_arn,
            pipelineArn=pipeline_arn,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            createdBy=created_by,
            lastUpdatedBy=last_updated_by,
        )

    return _get_mock_pipeline


@pytest.fixture()
def get_mock_mandatory_components_list():
    def _get_mandatory_component_versions():
        mandatory_component_versions = []
        for i in range(3):
            mandatory_component_versions.append(
                component_version_entry.ComponentVersionEntry(
                    componentId=f"comp-{i + 1}",
                    componentVersionId=f"vers-{i + 1}",
                    componentName=f"test-component-{i + 1}",
                    componentVersionName="1.0.0",
                    order=i + 1,
                )
            )
        return mandatory_component_versions

    def _get_mock_mandatory_components_list(
        platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        os: str = GlobalVariables.TEST_OS_VERSION.value,
        architecture: str = GlobalVariables.TEST_ARCHITECTURE.value,
        mandatory_component_versions: list[ComponentVersionEntry] = _get_mandatory_component_versions(),
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        created_by: str = GlobalVariables.TEST_CREATED_BY.value,
        last_updated_by: str = GlobalVariables.TEST_LAST_UPDATED_BY.value,
    ):
        return mandatory_components_list.MandatoryComponentsList(
            mandatoryComponentsListPlatform=platform,
            mandatoryComponentsListOsVersion=os,
            mandatoryComponentsListArchitecture=architecture,
            mandatoryComponentsVersions=mandatory_component_versions,
            createDate=create_date,
            lastUpdateDate=last_update_date,
            createdBy=created_by,
            lastUpdatedBy=last_updated_by,
        )

    return _get_mock_mandatory_components_list


@pytest.fixture()
def mock_aws_recipe_version_testing_service(mock_aws_recipe_version_testing_service_factory):
    return mock_aws_recipe_version_testing_service_factory()


@pytest.fixture()
def mock_aws_recipe_version_testing_service_factory(mock_system_configuration_mapping):
    def __inner(ami_factory_subnet_names: list[str] = GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value):
        return aws_recipe_version_testing_service.AwsRecipeVersionTestingService(
            admin_role=GlobalVariables.TEST_ADMIN_ROLE.value,
            ami_factory_aws_account_id=GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value,
            ami_factory_subnet_names=ami_factory_subnet_names,
            instance_security_group_name=GlobalVariables.TEST_INSTANCE_SECURITY_GROUP_NAME.value,
            region=GlobalVariables.TEST_REGION.value,
            system_configuration_mapping=mock_system_configuration_mapping,
            instance_profile_name=GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value,
            ssm_run_command_timeout=GlobalVariables.SSM_RUN_COMMAND_TIMEOUT.value,
            recipe_test_s3_bucket_name=GlobalVariables.TEST_RECIPE_TEST_BUCKET_NAME.value,
        )

    return __inner


@pytest.fixture()
def mock_aws_component_version_testing_service(mock_aws_component_version_testing_service_factory):
    return mock_aws_component_version_testing_service_factory()


@pytest.fixture()
def mock_aws_component_version_testing_service_factory(mock_system_configuration_mapping):
    def __inner(
        mock_system_configuration_mapping=mock_system_configuration_mapping,
        ami_factory_subnet_names: list[str] = GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value,
    ):
        return aws_component_version_testing_service.AwsComponentVersionTestingService(
            admin_role=GlobalVariables.TEST_ADMIN_ROLE.value,
            ami_factory_aws_account_id=GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value,
            ami_factory_subnet_names=ami_factory_subnet_names,
            instance_security_group_name=GlobalVariables.TEST_INSTANCE_SECURITY_GROUP_NAME.value,
            region=GlobalVariables.TEST_REGION.value,
            system_configuration_mapping=mock_system_configuration_mapping,
            volume_size=int(GlobalVariables.TEST_VOLUME_SIZE.value),
            instance_profile_name=GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value,
            ssm_run_command_timeout=GlobalVariables.SSM_RUN_COMMAND_TIMEOUT.value,
            component_test_s3_bucket_name=GlobalVariables.TEST_RECIPE_TEST_BUCKET_NAME.value,
        )

    return __inner


@pytest.fixture()
def mock_ami_ssm_param(mock_system_configuration_mapping, mock_ssm_client):
    mock_ssm_client.put_parameter(
        Name=mock_system_configuration_mapping.get(GlobalVariables.TEST_PLATFORM.value)
        .get(GlobalVariables.TEST_ARCHITECTURE.value)
        .get(GlobalVariables.TEST_OS_VERSION.value)
        .get(aws_component_version_testing_service.SystemConfigurationMappingAttributes.AMI_SSM_PARAM_NAME),
        Type="String",
        Value=GlobalVariables.TEST_AMI_ID.value,
    )


@pytest.fixture()
def mock_command_id(mock_ssm_client, mock_system_configuration_mapping):
    return (
        mock_ssm_client.send_command(
            CloudWatchOutputConfig={"CloudWatchOutputEnabled": True},
            DocumentName=mock_system_configuration_mapping.get(GlobalVariables.TEST_PLATFORM.value)
            .get(GlobalVariables.TEST_ARCHITECTURE.value)
            .get(GlobalVariables.TEST_OS_VERSION.value)
            .get(aws_component_version_testing_service.SystemConfigurationMappingAttributes.COMMAND_SSM_DOCUMENT_NAME),
            InstanceIds=[GlobalVariables.TEST_INSTANCE_ID.value],
            Parameters={
                "commands": [
                    mock_system_configuration_mapping.get(GlobalVariables.TEST_PLATFORM.value)
                    .get(GlobalVariables.TEST_ARCHITECTURE.value)
                    .get(GlobalVariables.TEST_OS_VERSION.value)
                    .get(
                        aws_component_version_testing_service.SystemConfigurationMappingAttributes.SETUP_TESTING_ENVIRONMENT_COMMAND
                    )
                ],
                "executionTimeout": [str(GlobalVariables.SSM_RUN_COMMAND_TIMEOUT.value)],
            },
        )
        .get("Command")
        .get("CommandId")
    )


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Mock AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", GlobalVariables.AWS_AWS_ACCESS_KEY_ID.value)
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", GlobalVariables.AWS_SECRET_ACCESS_KEY.value)
    monkeypatch.setenv("AWS_SECURITY_TOKEN", GlobalVariables.AWS_SECURITY_TOKEN.value)
    monkeypatch.setenv("AWS_SESSION_TOKEN", GlobalVariables.AWS_SESSION_TOKEN.value)
    monkeypatch.setenv("AWS_REGION", GlobalVariables.TEST_REGION.value)
    monkeypatch.setenv("AWS_DEFAULT_REGION", GlobalVariables.TEST_REGION.value)


@pytest.fixture()
def get_ec2_image_builder_component_srv():
    return ec2_image_builder_component_service.Ec2ImageBuilderComponentService(
        admin_role=GlobalVariables.TEST_ADMIN_ROLE.value,
        ami_factory_aws_account_id=GlobalVariables.AWS_ACCOUNT_ID.value,
        region=GlobalVariables.TEST_REGION.value,
    )


@pytest.fixture()
def get_ec2_image_builder_recipe_srv():
    return ec2_image_builder_recipe_service.Ec2ImageBuilderRecipeService(
        GlobalVariables.TEST_ADMIN_ROLE.value,
        GlobalVariables.AWS_ACCOUNT_ID.value,
        GlobalVariables.TEST_IMAGE_KEY_NAME.value,
        GlobalVariables.TEST_REGION.value,
    )


@pytest.fixture()
def get_parameter_srv():
    return parameter_service.ParameterService(
        GlobalVariables.TEST_ADMIN_ROLE.value,
        GlobalVariables.AWS_ACCOUNT_ID.value,
        GlobalVariables.TEST_REGION.value,
    )


@pytest.fixture()
def get_s3_srv():
    return aws_component_definition_service.AWSComponentDefinitionService(
        admin_role=GlobalVariables.TEST_ADMIN_ROLE.value,
        ami_factory_aws_account_id=GlobalVariables.AWS_ACCOUNT_ID.value,
        region=GlobalVariables.TEST_REGION.value,
        bucket_name=GlobalVariables.FAKE_BUCKET_NAME.value,
        bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        knowledge_base_id="test-knowledge-base-id",
        data_source_id="test-data-source-id",
        ai_system_prompt="Test system prompt for AI generation",
        max_context_results=3,
        max_tokens=4000,
        model_response_bucket_name="test-model-response-bucket",
    )


@pytest.fixture()
def get_test_ec2_image_builder_pipeline_srv(mock_pipelines_configuration_mapping):
    return ec2_image_builder_pipeline_service.Ec2ImageBuilderPipelineService(
        admin_role=GlobalVariables.TEST_ADMIN_ROLE.value,
        ami_factory_aws_account_id=GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value,
        ami_factory_subnet_names=GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value,
        image_key_name=GlobalVariables.TEST_IMAGE_KEY_NAME.value,
        instance_profile_name=GlobalVariables.TEST_INSTANCE_PROFILE_NAME.value,
        instance_security_group_name=GlobalVariables.TEST_INSTANCE_SECURITY_GROUP_NAME.value,
        pipelines_configuration_mapping=mock_pipelines_configuration_mapping,
        region=GlobalVariables.TEST_REGION.value,
        topic_arn=(
            f"arn:aws:sns:{GlobalVariables.TEST_REGION.value}"
            f":{GlobalVariables.TEST_AMI_FACTORY_AWS_ACCOUNT_ID.value}"
            f":{GlobalVariables.TEST_TOPIC_NAME.value}"
        ),
    )


@pytest.fixture
def get_mock_parameter(mock_ssm_client):
    def _get_mock_parameter(
        parameter_name: str = GlobalVariables.TEST_PARAMETER_NAME.value,
        parameter_value: str = GlobalVariables.TEST_PARAMETER_VALUE.value,
        parameter_type: str = GlobalVariables.TEST_PARAMETER_TYPE.value,
    ):
        return mock_ssm_client.put_parameter(
            Name=parameter_name,
            Value=parameter_value,
            Type=parameter_type,
            Overwrite=True,
        )

    return _get_mock_parameter
