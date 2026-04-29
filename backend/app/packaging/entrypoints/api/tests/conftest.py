import json
import os
from enum import Enum
from unittest import mock

import boto3
import moto
import pytest
from attr import dataclass
from aws_lambda_powertools.utilities.typing import LambdaContext
from moto import mock_aws
from openapi_spec_validator.readers import read_from_filename

from app.packaging.adapters.services import (
    aws_component_definition_service,
    ec2_image_builder_pipeline_service,
)
from app.packaging.domain.commands.component import (
    archive_component_command,
    create_component_command,
    create_component_version_command,
    create_mandatory_components_list_command,
    release_component_version_command,
    retire_component_version_command,
    share_component_command,
    update_component_command,
    update_component_version_command,
    update_mandatory_components_list_command,
)
from app.packaging.domain.commands.image import create_image_command
from app.packaging.domain.commands.pipeline import (
    create_pipeline_command,
    retire_pipeline_command,
    update_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    archive_recipe_command,
    create_recipe_command,
    create_recipe_version_command,
    release_recipe_version_command,
    retire_recipe_version_command,
    update_recipe_version_command,
)
from app.packaging.domain.model.component import (
    component,
    component_project_association,
    component_version,
    component_version_summary,
    component_version_test_execution,
    component_version_test_execution_summary,
    mandatory_components_list,
)
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import (
    recipe,
    recipe_version,
    recipe_version_summary,
    recipe_version_test_execution,
    recipe_version_test_execution_summary,
)
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.domain.ports import (
    component_version_query_service,
    parameter_service,
)
from app.packaging.domain.query_services import (
    component_domain_query_service,
    component_version_domain_query_service,
    component_version_test_execution_domain_query_service,
    image_domain_query_service,
    mandatory_components_list_domain_query_service,
    pipeline_domain_query_service,
    recipe_domain_query_service,
    recipe_version_domain_query_service,
    recipe_version_test_execution_domain_query_service,
)
from app.packaging.entrypoints.api import bootstrapper
from app.packaging.entrypoints.api.model import api_model
from app.shared.adapters.message_bus import in_memory_command_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.api import secrets_manager_api


class GlobalVariables(Enum):
    TEST_S3_LOG_PRESIGNED_URL = "https://example.com"
    TEST_LAST_UPDATED_BY = "T0011AA"
    TEST_LAST_UPDATE_DATE = "2000-01-01"
    TEST_CREATED_BY = "T0011AA"
    TEST_CREATE_DATE = "2000-01-01"
    TEST_PROJECT_ID = "proj-12345"
    TEST_AWS_ACCOUNT_ID = "123456789123"
    TEST_AWS_REGION = "us-east-1"
    TEST_GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY = "ami-01234567890abcdef"
    TEST_GSI_NAME_ENTITIES = "gsi_entities"
    TEST_GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
    TEST_REGION = "us-east-1"
    TEST_SECRET_NAME = "audit-logging-key"
    TEST_TABLE_NAME = "test-table"
    TEST_AMI_ID = "ami-01234567890abcdef"
    TEST_AMI_VERSION = "1.0.0"
    TEST_COMPONENT_ID = "comp-12345abc"
    TEST_COMPONENT_NAME = "proserve-autosar-component"
    TEST_COMPONENT_PLATFORM = "Linux"
    TEST_COMPONENT_SUPPORTED_ARCHITECTURES = ["amd64"]
    TEST_COMPONENT_SUPPORTED_OS_VERSIONS = ["Ubuntu 24"]
    TEST_COMPONENT_DESCRIPTION = "Test component"
    TEST_COMPONENT_VERSION_YAML_DEFINITION = (
        "---\nname: Software Install Google Chrome\ndescription: test\nschemaVersion: A\nphases: []"
    )
    TEST_COMPONENT_VERSION_RELEASE_TYPE = "Major"
    TEST_COMPONENT_VERSION_DESCRIPTION = "Test Description"
    TEST_COMPONENT_VERSION_ID = "version-12345abc"
    TEST_COMPONENT_VERSION_NAME = "1.0.0"
    TEST_COMPONENT_VERSION_TYPE = "MAIN"
    TEST_COMMAND_ID = "750ac01c-c984-4ea0-b16f-d79819930140"
    TEST_TEST_EXECUTION_ID = "c0220642-ced2-4f46-bea3-1601a70b5c55"
    TEST_TEST_EXECUTION_OUTPUT = "This is a test output"
    TEST_MANDATORY_COMPONENTS_LIST_LENGTH = 3
    TEST_RECIPE_ID = "reci-12345"
    TEST_RECIPE_NAME = "Test Recipe"
    TEST_RECIPE_DESCRIPTION = "Test Description"
    TEST_RECIPE_VERSION_RELEASE_TYPE = "MAJOR"
    TEST_RECIPE_VERSION_DESCRIPTION = "Test Description"
    TEST_RECIPE_VERSION_ID = "version-12345abc"
    TEST_RECIPE_VERSION_NAME = "1.0.0"
    TEST_RECIPE_VERSION_TEST_EXECUTION_ID = TEST_TEST_EXECUTION_ID
    TEST_RECIPE_VERSION_VOLUME_SIZE = "8"
    TEST_RECIPE_STATUS = "CREATED"
    TEST_INSTANCE_ID = "i-01234567890abcdef"
    TEST_PIPELINE_ID = "pipe-12345"
    TEST_PIPELINE_BUILD_INSTANCE_TYPES = ["m8a.2xlarge", "m8i.2xlarge"]
    TEST_PIPELINE_DESCRIPTION = "Test Pipeline"
    TEST_PIPELINE_NAME = "Test Pipeline"
    TEST_PIPELINE_SCHEDULE = "0 10 * * ? *"
    TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN = (
        f"arn:aws:imagebuilder:{TEST_REGION}:{TEST_AWS_ACCOUNT_ID}:distribution-configuration/{TEST_PIPELINE_ID}"
    )
    TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN = (
        f"arn:aws:imagebuilder:{TEST_REGION}:{TEST_AWS_ACCOUNT_ID}:infrastructure-configuration/{TEST_PIPELINE_ID}"
    )
    TEST_PIPELINE_PIPELINE_ARN = f"arn:aws:imagebuilder:{TEST_REGION}:123456789123:image-pipeline/{TEST_PIPELINE_ID}"
    TEST_IMAGE_ID = "image-12345"
    TEST_IMAGE_BUILD_VERSION = 1
    TEST_IMAGE_BUILD_VERSION_ARN = (
        f"arn:aws:imagebuilder:us-east-1:123456789012:image/{TEST_RECIPE_NAME}/{TEST_RECIPE_VERSION_NAME}/1"
    )
    TEST_IMAGE_KEY_NAME = "test-key"
    TEST_IMAGE_PARENT_UPSTREAM_ID = "ami-12345"
    TEST_IMAGE_UPSTREAM_ID = "ami-01234567890abcdef"
    TEST_PIPELINE_ALLOWED_BUILD_INSTANCE_TYPES = [
        "m8a.2xlarge",
        "m8i.2xlarge",
        "m8a.4xlarge",
        "m8i.4xlarge",
    ]
    TEST_DDB_TABLE_DEFINITION = {
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
            {"AttributeName": "entity", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "GlobalSecondaryIndexes": [
            {
                "IndexName": TEST_GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY,
                "KeySchema": [
                    {"AttributeName": "GSI_PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI_SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": TEST_GSI_NAME_ENTITIES,
                "KeySchema": [
                    {"AttributeName": "entity", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            },
            {
                "IndexName": TEST_GSI_NAME_INVERTED_PK,
                "KeySchema": [
                    {"AttributeName": "SK", "KeyType": "HASH"},
                    {"AttributeName": "PK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "KEYS_ONLY"},
            },
        ],
    }
    TEST_SOFTWARE_VENDOR = "vector"
    TEST_SOFTWARE_VERSION = "1.0.0"
    TEST_COMPONENT_LICENSE_DASHBOARD = "https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1"
    TEST_COMPONENT_SOFTWARE_VERSION_NOTES = "This is a test component software version."
    TEST_AMI_FACTORY_SUBNET_NAMES = "subnet-1a,subnet-1b"


@pytest.fixture
def lambda_context() -> LambdaContext.client_context:
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
    monkeypatch.setenv("AWS_REGION", GlobalVariables.TEST_REGION.value)
    monkeypatch.setenv("ADMIN_ROLE", "adminrole")
    monkeypatch.setenv("AWS_DEFAULT_REGION", GlobalVariables.TEST_REGION.value)
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "Projects")
    monkeypatch.setenv("AUDIT_LOGGING_KEY_NAME", GlobalVariables.TEST_SECRET_NAME.value)
    monkeypatch.setenv("SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME", "/test/param")
    monkeypatch.setenv("PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME", "/test/pipelines/param")
    monkeypatch.setenv("IMAGE_KEY_NAME", GlobalVariables.TEST_IMAGE_KEY_NAME.value)
    monkeypatch.setenv("AMI_FACTORY_SUBNET_NAMES", GlobalVariables.TEST_AMI_FACTORY_SUBNET_NAMES.value)
    monkeypatch.setenv("AMI_FACTORY_AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("AMI_FACTORY_VPC_NAME", "vpc-test")
    monkeypatch.setenv("API_BASE_PATH", "packaging")
    monkeypatch.setenv("COMPONENT_S3_BUCKET_NAME", "fake-bucket")
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_BUILD_VERSION_ARN", "gsi_build_version_arn")
    monkeypatch.setenv("GSI_NAME_CUSTOM_QUERY_BY_RECIPE_ID_AND_VERSION", "gsi_recipe_id_version")
    monkeypatch.setenv("GSI_NAME_IMAGE_UPSTREAM_ID", "gsi_image_upstream_id")
    monkeypatch.setenv("INSTANCE_PROFILE_NAME", "instance-profile-test")
    monkeypatch.setenv("INSTANCE_SECURITY_GROUP_NAME", "sg-test")
    monkeypatch.setenv("RECIPE_S3_BUCKET_NAME", "fake-recipe-bucket")
    monkeypatch.setenv("TOPIC_NAME", "test-topic")


@pytest.fixture(autouse=True)
def ssm_mock():
    with mock_aws():
        yield boto3.client(
            "ssm",
            region_name=GlobalVariables.TEST_REGION.value,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture(autouse=True)
def sts_mock():
    with mock_aws():
        yield boto3.client(
            "sts",
            region_name=GlobalVariables.TEST_REGION.value,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture(autouse=True)
def mock_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name="/test/param",
        Type="String",
        Value=json.dumps(
            {
                "Linux": {
                    "amd64": {
                        "Ubuntu 24": {
                            # Adding /test/ prefix since /aws/service/ is reserved and can't be mocked
                            "ami_ssm_param_name": "/test/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id",
                            "command_ssm_document_name": "AWS-RunShellScript",
                            "instance_type": "m8i.2xlarge",
                            "run_testing_command": "awstoe run --documents << documents >> --execution-id /<< instance_id >> --log-s3-bucket-name << log_s3_bucket_name >> --log-s3-key-prefix << object_id >>/<< version_id >> --trace",
                            "setup_testing_environment_command": "curl https://awstoe-us-east-1.s3.us-east-1.amazonaws.com/latest/linux/amd64/awstoe --output /usr/bin/awstoe && chmod +x /usr/bin/awstoe",
                        },
                    },
                },
            }
        ),
    )


@pytest.fixture(autouse=True)
def mock_pipelines_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name="/test/pipelines/param",
        Type="String",
        Value=json.dumps(
            {
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
        ),
    )


@pytest.fixture(autouse=True)
def mock_ami_parameter_value(ssm_mock):
    ssm_mock.put_parameter(
        Name="/test/aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id",
        Type="String",
        Value="ami-01234567890abcdef",
    )


@pytest.fixture(autouse=True)
def mock_ai_system_prompt_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name="/test/shared/ai-system-prompt",
        Type="String",
        Value="Test AI system prompt for EC2 Image Builder component generation.",
    )


@pytest.fixture
def api_schema():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(
        current_dir,
        "..",
        "schema",
        "proserve-workbench-packaging-api-schema.yaml",
    )
    spec_dict, base_uri = read_from_filename(schema_path)
    return spec_dict


@pytest.fixture
def authenticated_event(cognito_user_pool_mock, mock_cognito_user):
    user_sub_attribute = [x for x in mock_cognito_user["User"]["Attributes"] if x["Name"].lower() == "sub"][0]

    def _authenticated_event(body, path, http_method, query_params=None):
        return {
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
                    "userName": GlobalVariables.TEST_CREATED_BY.value,
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
                "requestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "identity": {
                    "cognitoIdentityPoolId": "us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "accountId": "111111111111",
                    "cognitoIdentityId": "us-east-1:xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                    "caller": "AROXXXXXXXXXXXXXXXXX:CognitoIdentityCredentials",
                    "sourceIp": "0.0.0.0",
                    "principalOrgId": "o-xxxxxxxxxx",
                    "accessKey": "AXXXXXXXXXXXXXXXXXXXXX",
                    "cognitoAuthenticationType": "authenticated",
                    "cognitoAuthenticationProvider": f"cognito-idp.us-east-1.amazonaws.com/us-east-1_00000000,cognito-idp.us-east-1.amazonaws.com/{cognito_user_pool_mock['UserPool']['Id']}:CognitoSignIn:{user_sub_attribute['Value']}",
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


@pytest.fixture()
def cognito_identity_mock():
    with mock_aws():
        yield boto3.client("cognito-idp", region_name=GlobalVariables.TEST_REGION.value)


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


@pytest.fixture(autouse=True)
def mock_secrets_manager():
    with mock_aws():
        yield boto3.client(
            "secretsmanager",
            region_name=GlobalVariables.TEST_REGION.value,
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
        )


@pytest.fixture(autouse=True)
def mock_audit_logging_secret(mock_secrets_manager):
    secrets_manager = secrets_manager_api.SecretsManagerAPI(
        region=GlobalVariables.TEST_REGION.value,
        access_key_id="access_key_id",
        secret_access_key="secret_access_key",
        session_token="session_token",
    )

    return secrets_manager.create_secret(name=GlobalVariables.TEST_SECRET_NAME.value, value="test123")


@pytest.fixture()
def parameter_service_mock():
    return mock.create_autospec(spec=parameter_service.ParameterDefinitionService)


@pytest.fixture()
def pipeline_service_mock():
    return mock.create_autospec(spec=parameter_service.ParameterDefinitionService)


@pytest.fixture()
def generic_repo_mock():
    return mock.create_autospec(spec=unit_of_work.GenericRepository, instance=True)


@pytest.fixture()
def uow_mock(generic_repo_mock):
    uow_mock = mock.create_autospec(spec=unit_of_work.UnitOfWork, instance=True)
    uow_mock.get_repository.return_value = generic_repo_mock
    return uow_mock


@pytest.fixture()
def component_version_query_service_mock():
    component_version_qry_srv = mock.create_autospec(spec=component_version_query_service.ComponentVersionQueryService)

    return component_version_qry_srv


@pytest.fixture
def mock_dynamodb():
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture
def mock_s3(mock_dynamodb):
    yield boto3.client("s3", region_name=GlobalVariables.TEST_REGION.value)


@pytest.fixture(autouse=True)
def backend_app_dynamodb_table(mock_dynamodb):
    table = mock_dynamodb.create_table(**GlobalVariables.TEST_DDB_TABLE_DEFINITION.value)
    table.meta.client.get_waiter("table_exists").wait(TableName=GlobalVariables.TEST_TABLE_NAME.value)
    return table


@pytest.fixture()
def mock_events_client():
    with moto.mock_aws():
        yield boto3.client("events", GlobalVariables.TEST_REGION.value)


@pytest.fixture(autouse=True)
def mock_event_bus(mock_events_client):
    return mock_events_client.create_event_bus(Name="test-eb")


@pytest.fixture(autouse=True)
def lambda_env_vars(monkeypatch, mock_event_bus):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("TABLE_NAME", GlobalVariables.TEST_TABLE_NAME.value)
    monkeypatch.setenv(
        "GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY",
        GlobalVariables.TEST_GSI_NAME_CUSTOM_QUERY_BY_STATUS_KEY.value,
    )
    monkeypatch.setenv("GSI_NAME_ENTITIES", GlobalVariables.TEST_GSI_NAME_ENTITIES.value)
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", GlobalVariables.TEST_GSI_NAME_INVERTED_PK.value)
    monkeypatch.setenv("DOMAIN_EVENT_BUS_ARN", mock_event_bus.get("EventBusArn"))
    monkeypatch.setenv("BOUNDED_CONTEXT", "packaging.bc.test")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("AWS_DEFAULT_REGION", GlobalVariables.TEST_REGION.value)
    monkeypatch.setenv("PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME", "/test/pipelines/param")


@pytest.fixture()
def create_component(authenticated_event, lambda_context):
    def _create_component(
        component_name: str = GlobalVariables.TEST_COMPONENT_NAME.value,
        component_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        component_supported_architectures=None,
        component_supported_os_versions=None,
        component_description: str = GlobalVariables.TEST_COMPONENT_DESCRIPTION.value,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        if component_supported_os_versions is None:
            component_supported_os_versions = list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value)
        if component_supported_architectures is None:
            component_supported_architectures = list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value)
        request = api_model.CreateComponentRequest(
            componentName=component_name,
            componentPlatform=component_platform,
            componentSupportedArchitectures=component_supported_architectures,
            componentSupportedOsVersions=component_supported_os_versions,
            componentDescription=component_description,
        )

        evt = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/components", "POST")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], result["body"]

    return _create_component


@pytest.fixture()
def archive_component(authenticated_event, lambda_context):
    def _archive_component(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        component_id: str = GlobalVariables.TEST_COMPONENT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/components/{component_id}", "DELETE")
        result = handler.handler(evt, lambda_context)

        return result["statusCode"], json.loads(result["body"])

    return _archive_component


@pytest.fixture()
def list_components(authenticated_event, lambda_context):
    def _list_components(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/components", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_components


@pytest.fixture()
def share_component(authenticated_event, lambda_context):
    def _share_component(
        project_ids: list[str],
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        component_id: str = GlobalVariables.TEST_COMPONENT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        request = api_model.ShareComponentRequest(
            projectIds=project_ids,
        )

        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/components/{component_id}",
            "POST",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _share_component


@pytest.fixture()
def update_component(authenticated_event, lambda_context):
    def _update_component(
        component_id: str,
        component_description: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        request = api_model.UpdateComponentRequest(
            componentDescription=component_description,
        )

        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/components/{component_id}",
            "PUT",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _update_component


@pytest.fixture()
def get_component(authenticated_event, lambda_context):
    def _get_component(
        component_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/components/{component_id}", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_component


@pytest.fixture()
def create_component_version(authenticated_event, lambda_context):
    def _create_component_version(
        component_id: str,
        component_version_description: str = GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value,
        component_version_release_type: str = GlobalVariables.TEST_COMPONENT_VERSION_RELEASE_TYPE.value,
        component_version_yaml_definition: str = GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value,
        component_version_dependencies: list[component_version_entry.ComponentVersionEntry] = [],
        software_vendor: str = GlobalVariables.TEST_SOFTWARE_VENDOR.value,
        software_version: str = GlobalVariables.TEST_SOFTWARE_VERSION.value,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        optional_fields=None,
    ):
        from app.packaging.entrypoints.api import handler

        kwargs = {
            "componentVersionDescription": component_version_description,
            "componentVersionReleaseType": component_version_release_type,
            "componentVersionYamlDefinition": component_version_yaml_definition,
            "componentVersionDependencies": component_version_dependencies,
            "softwareVendor": software_vendor,
            "softwareVersion": software_version,
        }
        if optional_fields:
            for field, value in optional_fields.items():
                if value:
                    kwargs[field] = value

        request = api_model.CreateComponentVersionRequest(**kwargs)
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/components/{component_id}/versions",
            "POST",
        )
        result = handler.handler(evt, lambda_context)

        return result["statusCode"], json.loads(result["body"])

    return _create_component_version


@pytest.fixture()
def validate_component_version(authenticated_event, lambda_context):
    def _validate_component_version(
        component_id: str,
        component_version_description: str = GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value,
        component_version_release_type: str = GlobalVariables.TEST_COMPONENT_VERSION_RELEASE_TYPE.value,
        component_version_yaml_definition: str = GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value,
        component_version_dependencies: list[component_version_entry.ComponentVersionEntry] = [],
        software_vendor: str = GlobalVariables.TEST_SOFTWARE_VENDOR.value,
        software_version: str = GlobalVariables.TEST_SOFTWARE_VERSION.value,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        optional_fields=None,
    ):
        from app.packaging.entrypoints.api import handler

        kwargs = {
            "componentVersionDescription": component_version_description,
            "componentVersionReleaseType": component_version_release_type,
            "componentVersionYamlDefinition": component_version_yaml_definition,
            "componentVersionDependencies": component_version_dependencies,
            "softwareVendor": software_vendor,
            "softwareVersion": software_version,
        }
        if optional_fields:
            for field, value in optional_fields.items():
                if value:
                    kwargs[field] = value

        request = api_model.CreateComponentVersionRequest(**kwargs)
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/components/{component_id}/validateVersions",
            "POST",
        )
        result = handler.handler(evt, lambda_context)

        return result["statusCode"], json.loads(result["body"])

    return _validate_component_version


@pytest.fixture()
def get_component_versions(authenticated_event, lambda_context):
    def _get_component_versions(
        component_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/components/{component_id}/versions", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_component_versions


@pytest.fixture()
def get_component_version(authenticated_event, lambda_context):
    def _get_component_version(
        component_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/components/{component_id}/versions/{version_id}",
            "GET",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_component_version


@pytest.fixture()
def retire_component_version(authenticated_event, lambda_context):
    def _retire_component_version(
        component_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/components/{component_id}/versions/{version_id}",
            "DELETE",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _retire_component_version


@pytest.fixture()
def release_component_version(authenticated_event, lambda_context):
    def _release_component_version(
        component_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            json.dumps({}),
            f"/projects/{project_id}/components/{component_id}/versions/{version_id}",
            "POST",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _release_component_version


@pytest.fixture()
def update_component_version(authenticated_event, lambda_context):
    def _update_component_version(
        component_id: str,
        version_id: str,
        component_version_description: str = GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value,
        component_version_yaml_definition: str = GlobalVariables.TEST_COMPONENT_VERSION_YAML_DEFINITION.value,
        component_version_dependencies: list[component_version_entry.ComponentVersionEntry] = [],
        software_vendor: str = GlobalVariables.TEST_SOFTWARE_VENDOR.value,
        software_version: str = GlobalVariables.TEST_SOFTWARE_VERSION.value,
        license_dashboard: str = GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value,
        notes: str = GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        request = api_model.UpdateComponentVersionRequest(
            componentVersionDescription=component_version_description,
            componentVersionYamlDefinition=component_version_yaml_definition,
            componentVersionDependencies=[
                dep.model_dump() if hasattr(dep, "model_dump") else dep for dep in component_version_dependencies
            ],
            softwareVendor=software_vendor,
            softwareVersion=software_version,
            licenseDashboard=license_dashboard,
            notes=notes,
        )
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/components/{component_id}/versions/{version_id}",
            "PUT",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _update_component_version


@pytest.fixture()
def get_released_component_versions(authenticated_event, lambda_context):
    def _get_released_component_versions(
        parameters: dict,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/components-versions", "GET", parameters)
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_released_component_versions


@pytest.fixture()
def get_component_version_test_executions(authenticated_event, lambda_context):
    def _get_component_version_test_executions(
        component_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/components/{component_id}/versions/{version_id}/test-executions",
            "GET",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_component_version_test_executions


@pytest.fixture()
def get_component_version_test_execution_logs_url(authenticated_event, lambda_context):
    def _get_component_version_test_execution_logs_url(
        component_id: str,
        version_id: str,
        execution_id: str,
        instance_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/components/{component_id}/versions/{version_id}/test-executions/{execution_id}/{instance_id}/logs-url",
            "GET",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_component_version_test_execution_logs_url


@pytest.fixture()
def delete_component_version(authenticated_event, lambda_context):
    def _delete_component_version(
        component_id: str,
        component_version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/components/{component_id}/versions/{component_version_id}",
            "DELETE",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _delete_component_version


@pytest.fixture()
def create_recipe(authenticated_event, lambda_context):
    def _create_recipe(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_name: str = GlobalVariables.TEST_RECIPE_NAME.value,
        recipe_description: str = GlobalVariables.TEST_RECIPE_DESCRIPTION.value,
        recipe_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        recipe_architecture: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
        recipe_os_version: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
        create_date: str = GlobalVariables.TEST_CREATE_DATE.value,
        created_by: str = GlobalVariables.TEST_CREATED_BY.value,
        last_update_date: str = GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        last_updated_by: str = GlobalVariables.TEST_LAST_UPDATED_BY.value,
    ):
        from app.packaging.entrypoints.api import handler

        request = api_model.CreateRecipeRequest(
            recipeName=recipe_name,
            recipePlatform=recipe_platform,
            recipeDescription=recipe_description,
            recipeArchitecture=recipe_architecture,
            recipeOsVersion=recipe_os_version,
            createDate=create_date,
            createdBy=created_by,
            lastUpdateDate=last_update_date,
            lastUpdatedBy=last_updated_by,
        )
        evt = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/recipes", "POST")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _create_recipe


@pytest.fixture()
def archive_recipe(authenticated_event, lambda_context):
    def _archive_recipe(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_id: str = GlobalVariables.TEST_RECIPE_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/recipes/{recipe_id}", "DELETE")
        result = handler.handler(evt, lambda_context)

        return result["statusCode"], json.loads(result["body"])

    return _archive_recipe


@pytest.fixture()
def list_recipes(authenticated_event, lambda_context):
    def _list_recipes(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/recipes", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_recipes


@pytest.fixture()
def get_recipe(authenticated_event, lambda_context):
    def _get_recipe(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_id: str = GlobalVariables.TEST_RECIPE_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/recipes/{recipe_id}", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_recipe


@pytest.fixture()
def create_recipe_version(authenticated_event, lambda_context):
    def _create_recipe_version(
        recipe_id: str,
        recipe_version_components_versions: list[api_model.RecipeComponentVersion],
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_version_description: str = GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
        recipe_version_release_type: str = GlobalVariables.TEST_RECIPE_VERSION_RELEASE_TYPE.value,
        recipe_version_volume_size: str = GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
    ):
        from app.packaging.entrypoints.api import handler

        request = api_model.CreateRecipeVersionRequest(
            recipeComponentsVersions=recipe_version_components_versions,
            recipeVersionDescription=recipe_version_description,
            recipeVersionReleaseType=recipe_version_release_type,
            recipeVersionVolumeSize=recipe_version_volume_size,
        )
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/recipes/{recipe_id}/versions",
            "POST",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _create_recipe_version


@pytest.fixture()
def list_recipe_versions(authenticated_event, lambda_context):
    def _list_recipe_versions(
        recipe_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/recipes/{recipe_id}/versions", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_recipe_versions


@pytest.fixture()
def list_recipes_versions(authenticated_event, lambda_context):
    def _list_recipes_versions(
        recipe_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        status: str = "VALIDATED",
    ):
        from app.packaging.entrypoints.api import handler

        parameters = {"status": status}

        evt = authenticated_event(None, f"/projects/{project_id}/recipes-versions", "GET", parameters)
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_recipes_versions


@pytest.fixture()
def retire_recipe_version(authenticated_event, lambda_context):
    def _retire_recipe_version(
        recipe_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/recipes/{recipe_id}/versions/{version_id}",
            "DELETE",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _retire_recipe_version


@pytest.fixture()
def delete_recipe_version(authenticated_event, lambda_context):
    def _delete_recipe_version(
        recipe_id: str,
        recipe_version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/recipes/{recipe_id}/versions/{recipe_version_id}",
            "DELETE",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _delete_recipe_version


@pytest.fixture()
def get_recipe_version(authenticated_event, lambda_context):
    def _get_recipe_version(
        recipe_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/recipes/{recipe_id}/versions/{version_id}",
            "GET",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_recipe_version


@pytest.fixture()
def update_recipe_version(authenticated_event, lambda_context):
    def _update_recipe_version(
        recipe_id: str,
        recipe_version_id: str,
        recipe_version_components_versions: list[api_model.RecipeComponentVersion],
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_version_description: str = GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
        recipe_version_volume_size: str = GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
    ):
        from app.packaging.entrypoints.api import handler

        request = api_model.UpdateRecipeVersionRequest(
            recipeComponentsVersions=recipe_version_components_versions,
            recipeVersionDescription=recipe_version_description,
            recipeVersionVolumeSize=recipe_version_volume_size,
        )
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/recipes/{recipe_id}/versions/{recipe_version_id}",
            "PUT",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _update_recipe_version


@pytest.fixture()
def release_recipe_version(authenticated_event, lambda_context):
    def _release_recipe_version(
        recipe_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/recipes/{recipe_id}/versions/{version_id}",
            "POST",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _release_recipe_version


@pytest.fixture()
def list_recipe_version_test_executions(authenticated_event, lambda_context):
    def _list_recipe_version_test_executions(
        recipe_id: str,
        version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/recipes/{recipe_id}/versions/{version_id}/test-executions",
            "GET",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_recipe_version_test_executions


@pytest.fixture()
def get_recipe_version_test_execution_logs_url(authenticated_event, lambda_context):
    def _get_recipe_version_test_execution_logs_url(
        recipe_id: str,
        version_id: str,
        execution_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(
            None,
            f"/projects/{project_id}/recipes/{recipe_id}/versions/{version_id}/test-executions/{execution_id}/logs-url",
            "GET",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_recipe_version_test_execution_logs_url


@pytest.fixture()
def create_mandatory_components_list(authenticated_event, lambda_context):
    def _create_mandatory_components_list(
        mandatory_components_versions: list[api_model.ComponentVersionEntry] = None,
        prepended_components_versions: list[api_model.ComponentVersionEntry] = None,
        appended_components_versions: list[api_model.ComponentVersionEntry] = None,
        mandatory_component_list_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        mandatory_component_list_architecture: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
        mandatory_component_list_os: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        # Support both old and new API formats
        if mandatory_components_versions is not None:
            # Old format for backward compatibility - convert to new format with all as prepended
            request = api_model.CreateMandatoryComponentsListRequest(
                mandatoryComponentsListPlatform=mandatory_component_list_platform,
                mandatoryComponentsListArchitecture=mandatory_component_list_architecture,
                mandatoryComponentsListOsVersion=mandatory_component_list_os,
                prependedComponentsVersions=mandatory_components_versions,
                appendedComponentsVersions=[],
            )
        else:
            # New format with prepended/appended
            request = api_model.CreateMandatoryComponentsListRequest(
                mandatoryComponentsListPlatform=mandatory_component_list_platform,
                mandatoryComponentsListArchitecture=mandatory_component_list_architecture,
                mandatoryComponentsListOsVersion=mandatory_component_list_os,
                prependedComponentsVersions=prepended_components_versions or [],
                appendedComponentsVersions=appended_components_versions or [],
            )
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/mandatory-components-list",
            "POST",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _create_mandatory_components_list


@pytest.fixture()
def update_mandatory_components_list(authenticated_event, lambda_context):
    def _update_mandatory_components_list(
        mandatory_components_versions: list[api_model.ComponentVersionEntry] = None,
        prepended_components_versions: list[api_model.ComponentVersionEntry] = None,
        appended_components_versions: list[api_model.ComponentVersionEntry] = None,
        mandatory_component_list_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        mandatory_component_list_architecture: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
        mandatory_component_list_os: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        # Support both old and new API formats
        if mandatory_components_versions is not None:
            # Old format for backward compatibility - convert to new format with all as prepended
            request = api_model.UpdateMandatoryComponentsListRequest(
                mandatoryComponentsListPlatform=mandatory_component_list_platform,
                mandatoryComponentsListArchitecture=mandatory_component_list_architecture,
                mandatoryComponentsListOsVersion=mandatory_component_list_os,
                prependedComponentsVersions=mandatory_components_versions,
                appendedComponentsVersions=[],
            )
        else:
            # New format with prepended/appended
            request = api_model.UpdateMandatoryComponentsListRequest(
                mandatoryComponentsListPlatform=mandatory_component_list_platform,
                mandatoryComponentsListArchitecture=mandatory_component_list_architecture,
                mandatoryComponentsListOsVersion=mandatory_component_list_os,
                prependedComponentsVersions=prepended_components_versions or [],
                appendedComponentsVersions=appended_components_versions or [],
            )
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/mandatory-components-list",
            "PUT",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _update_mandatory_components_list


@pytest.fixture()
def get_mandatory_component_list(authenticated_event, lambda_context):
    def _get_mandatory_component_list(
        mandatory_component_list_platform: str = GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        mandatory_component_list_architecture: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
        mandatory_component_list_os: str = GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        params = {
            "mandatoryComponentsListOsVersion": mandatory_component_list_os,
            "mandatoryComponentsListPlatform": mandatory_component_list_platform,
            "mandatoryComponentsListArchitecture": mandatory_component_list_architecture,
        }
        evt = authenticated_event(None, f"/projects/{project_id}/mandatory-components-list", "GET", params)
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_mandatory_component_list


@pytest.fixture()
def list_mandatory_components_list(authenticated_event, lambda_context):
    def _list_mandatory_components_list(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/mandatory-components-lists", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_mandatory_components_list


@pytest.fixture()
def update_component_version_status(authenticated_event, lambda_context, backend_app_dynamodb_table):
    def _update_component_version_status(
        component_id: str,
        component_version_id: str,
        component_version_status: str,
    ):
        backend_app_dynamodb_table.update_item(
            Key={
                "PK": f"COMPONENT#{component_id}",
                "SK": f"VERSION#{component_version_id}",
            },
            AttributeUpdates={
                "status": {"Value": component_version_status},
                "componentBuildVersionArn": {
                    "Value": (
                        f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}"
                        f":{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:component/"
                        f"{component_id}/{component_version_id}"
                    )
                },
            },
        )
        return None

    return _update_component_version_status


@pytest.fixture()
def update_recipe_version_status(authenticated_event, lambda_context, backend_app_dynamodb_table):
    def _update_recipe_version_status(
        recipe_id: str,
        recipe_version_id: str,
        recipe_version_status: str,
    ):
        backend_app_dynamodb_table.update_item(
            Key={
                "PK": f"RECIPE#{recipe_id}",
                "SK": f"VERSION#{recipe_version_id}",
            },
            AttributeUpdates={
                "status": {"Value": recipe_version_status},
            },
        )
        return None

    return _update_recipe_version_status


@pytest.fixture()
def create_pipeline(authenticated_event, lambda_context):
    def _create_pipeline(
        recipe_id: str,
        recipe_version_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        build_instance_types=None,
        pipeline_description: str = GlobalVariables.TEST_PIPELINE_DESCRIPTION.value,
        pipeline_name: str = GlobalVariables.TEST_PIPELINE_NAME.value,
        pipeline_schedule: str = GlobalVariables.TEST_PIPELINE_SCHEDULE.value,
    ):
        from app.packaging.entrypoints.api import handler

        if build_instance_types is None:
            build_instance_types = list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value)
        request = api_model.CreatePipelineRequest(
            buildInstanceTypes=build_instance_types,
            pipelineDescription=pipeline_description,
            pipelineName=pipeline_name,
            pipelineSchedule=pipeline_schedule,
            recipeId=recipe_id,
            recipeVersionId=recipe_version_id,
        )
        evt = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/pipelines", "POST")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _create_pipeline


@pytest.fixture()
def list_pipelines(authenticated_event, lambda_context):
    def _list_pipelines(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/pipelines", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_pipelines


@pytest.fixture()
def get_pipelines_allowed_build_types(authenticated_event, lambda_context):
    def _get_pipelines_allowed_build_types(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_id: str = GlobalVariables.TEST_RECIPE_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        parameters = {"recipeId": recipe_id}
        evt = authenticated_event(
            None,
            f"/projects/{project_id}/allowed-build-instance-types",
            "GET",
            parameters,
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_pipelines_allowed_build_types


@pytest.fixture()
def update_pipeline_status(authenticated_event, lambda_context, backend_app_dynamodb_table):
    def _update_pipeline_status(
        pipeline_id: str,
        pipeline_status: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        backend_app_dynamodb_table.update_item(
            Key={
                "PK": f"PROJECT#{project_id}",
                "SK": f"PIPELINE#{pipeline_id}",
            },
            AttributeUpdates={
                "status": {"Value": pipeline_status},
                "pipelineArn": {
                    "Value": (
                        f"arn:aws:imagebuilder:{GlobalVariables.TEST_REGION.value}:"
                        f"{GlobalVariables.TEST_AWS_ACCOUNT_ID.value}:image-pipeline/{pipeline_id}"
                    )
                },
            },
        )
        return None

    return _update_pipeline_status


@pytest.fixture()
def get_pipeline(authenticated_event, lambda_context):
    def _get_pipeline(
        pipeline_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/pipelines/{pipeline_id}", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_pipeline


@pytest.fixture()
def update_pipeline(authenticated_event, lambda_context):
    def _update_pipeline(
        pipeline_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
        recipe_version_id=None,
        build_instance_types=None,
        pipeline_schedule=None,
    ):
        from app.packaging.entrypoints.api import handler

        kwargs = {}
        if build_instance_types is not None:
            kwargs["buildInstanceTypes"] = build_instance_types
        if pipeline_schedule is not None:
            kwargs["pipelineSchedule"] = pipeline_schedule
        if recipe_version_id is not None:
            kwargs["recipeVersionId"] = recipe_version_id
        request = api_model.UpdatePipelineRequest(
            pipelineId=pipeline_id,
            **kwargs,
        )
        evt = authenticated_event(
            json.dumps(request.model_dump()),
            f"/projects/{project_id}/pipelines/{pipeline_id}",
            "PUT",
        )
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _update_pipeline


@pytest.fixture()
def retire_pipeline(authenticated_event, lambda_context):
    def _retire_pipeline(
        pipeline_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/pipelines/{pipeline_id}", "DELETE")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _retire_pipeline


@pytest.fixture()
def create_image(authenticated_event, lambda_context):
    def _create_image(pipeline_id: str, project_id: str = GlobalVariables.TEST_PROJECT_ID.value):
        request = api_model.CreateImageRequest(
            pipelineId=pipeline_id,
        )
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(json.dumps(request.model_dump()), f"/projects/{project_id}/images", "POST")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _create_image


@pytest.fixture()
def list_images(authenticated_event, lambda_context):
    def _list_images(
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/images", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _list_images


@pytest.fixture()
def get_image(authenticated_event, lambda_context):
    def _get_image(
        image_id: str,
        project_id: str = GlobalVariables.TEST_PROJECT_ID.value,
    ):
        from app.packaging.entrypoints.api import handler

        evt = authenticated_event(None, f"/projects/{project_id}/images/{image_id}", "GET")
        result = handler.handler(evt, lambda_context)
        return result["statusCode"], json.loads(result["body"])

    return _get_image


@pytest.fixture()
def get_test_component_yaml_definition():
    def _get_test_component_yaml_definition():
        # Ref: https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-use-documents.html#document-example
        component_yaml_definition = """
        name: LinuxBin
        description: Download and run a custom Linux binary file.
        schemaVersion: 1.0
        phases:
          - name: build
            steps:
              - name: Download
                action: S3Download
                inputs:
                  - source: s3://<replaceable>mybucket</replaceable>/<replaceable>myapplication</replaceable>
                    destination: /tmp/<replaceable>myapplication</replaceable>
              - name: Enable
                action: ExecuteBash
                onFailure: Continue
                inputs:
                  commands:
                    - 'chmod u+x {{ build.Download.inputs[0].destination }}'
              - name: Install
                action: ExecuteBinary
                onFailure: Continue
                inputs:
                  path: '{{ build.Download.inputs[0].destination }}'
                  arguments:
                    - '--install'
              - name: Delete
                action: DeleteFile
                inputs:
                  - path: '{{ build.Download.inputs[0].destination }}'
        """
        return component_yaml_definition

    return _get_test_component_yaml_definition


@pytest.fixture()
def get_mock_mandatory_components_list():
    def _get_mock_mandatory_components_list(
        mandatory_components_list_length: int = GlobalVariables.TEST_MANDATORY_COMPONENTS_LIST_LENGTH.value,
    ):
        mandatory_components_versions = []
        for i in range(mandatory_components_list_length):
            mandatory_components_versions.append(
                component_version_entry.ComponentVersionEntry(
                    componentId=f"comp-{i + 1}",
                    componentVersionId=f"vers-{i + 1}",
                    componentName=f"test-component-{i + 1}",
                    componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                    order=i + 1,
                    position="PREPEND",  # Default to PREPEND for backward compatibility
                )
            )
        mandatory_components_list_entity = mandatory_components_list.MandatoryComponentsList(
            mandatoryComponentsListPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            mandatoryComponentsListOsVersion=GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
            mandatoryComponentsListArchitecture=GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
            mandatoryComponentsVersions=mandatory_components_versions,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        return mandatory_components_list_entity

    return _get_mock_mandatory_components_list


@pytest.fixture
def mocked_component_domain_query_service() -> component_domain_query_service.ComponentDomainQueryService:
    component_domain_query_service_mock = mock.create_autospec(
        spec=component_domain_query_service.ComponentDomainQueryService
    )

    component_domain_query_service_mock.get_components.return_value = [
        component.Component(
            componentId=f"proj-{i}",
            componentDescription=GlobalVariables.TEST_COMPONENT_DESCRIPTION.value,
            componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
            componentPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            componentSupportedArchitectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
            componentSupportedOsVersions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
            status=component.ComponentStatus.Created,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        for i in range(2)
    ]
    component_domain_query_service_mock.get_component.return_value = component.Component(
        componentId=GlobalVariables.TEST_COMPONENT_ID.value,
        componentDescription=GlobalVariables.TEST_COMPONENT_DESCRIPTION.value,
        componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
        componentPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        componentSupportedArchitectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
        componentSupportedOsVersions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
        status=component.ComponentStatus.Created,
        createDate=GlobalVariables.TEST_CREATE_DATE.value,
        createdBy=GlobalVariables.TEST_CREATED_BY.value,
        lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
    )
    component_domain_query_service_mock.get_component_project_associations.return_value = [
        component_project_association.ComponentProjectAssociation(
            projectId=f"comp-{i}",
            componentId=GlobalVariables.TEST_COMPONENT_ID.value,
            componentDescription=GlobalVariables.TEST_COMPONENT_DESCRIPTION.value,
            componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
            componentPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            componentSupportedArchitectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
            componentSupportedOsVersions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        for i in range(2)
    ]

    return component_domain_query_service_mock


@pytest.fixture
def mocked_component_versions_domain_query_service() -> (
    component_version_domain_query_service.ComponentVersionDomainQueryService
):
    versions_domain_query_service_mock = mock.create_autospec(
        spec=component_version_domain_query_service.ComponentVersionDomainQueryService
    )

    versions_domain_query_service_mock.get_latest_component_version_name.return_value = "1.1.0-rc.1"
    versions_domain_query_service_mock.get_component_versions.return_value = [
        component_version.ComponentVersion(
            componentId=GlobalVariables.TEST_COMPONENT_ID.value,
            componentVersionId=f"version-{i}",
            componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
            componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
            componentVersionDescription=GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value,
            componentPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            componentSupportedArchitectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
            componentSupportedOsVersions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
            softwareVendor=GlobalVariables.TEST_SOFTWARE_VENDOR.value,
            softwareVersion=GlobalVariables.TEST_SOFTWARE_VERSION.value,
            licenseDashboard=GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value,
            notes=GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value,
            status=component_version.ComponentVersionStatus.Creating,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        for i in range(2)
    ]
    versions_domain_query_service_mock.get_component_version.return_value = (
        component_version.ComponentVersion(
            componentId=GlobalVariables.TEST_COMPONENT_ID.value,
            componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
            componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
            componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
            componentVersionDescription=GlobalVariables.TEST_COMPONENT_VERSION_DESCRIPTION.value,
            componentPlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            componentSupportedArchitectures=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value),
            componentSupportedOsVersions=list(GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value),
            softwareVendor=GlobalVariables.TEST_SOFTWARE_VENDOR.value,
            softwareVersion=GlobalVariables.TEST_SOFTWARE_VERSION.value,
            licenseDashboard=GlobalVariables.TEST_COMPONENT_LICENSE_DASHBOARD.value,
            notes=GlobalVariables.TEST_COMPONENT_SOFTWARE_VERSION_NOTES.value,
            status=component_version.ComponentVersionStatus.Creating,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        ),
        {"example_key": "example_value"},
        "ZXhhbXBsZV9rZXk6IGV4YW1wbGVfdmFsdWU=",
    )

    components_versions_summary_list = list()
    for i in range(2):
        for j in range(3):
            components_versions_summary_list.append(
                component_version_summary.ComponentVersionSummary(
                    componentId=f"comp-{i}",
                    componentVersionId=f"vers-{i}-{j}",
                    componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                    componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                )
            )
    versions_domain_query_service_mock.get_all_components_versions.return_value = components_versions_summary_list

    return versions_domain_query_service_mock


@pytest.fixture
def mocked_component_test_executions_domain_query_service() -> (
    component_version_test_execution_domain_query_service.ComponentVersionTestExecutionDomainQueryService
):
    test_executions_domain_query_service_mock = mock.create_autospec(
        spec=component_version_test_execution_domain_query_service.ComponentVersionTestExecutionDomainQueryService,
    )

    test_executions_domain_query_service_mock.get_component_version_test_execution_summaries.return_value = [
        component_version_test_execution_summary.ComponentVersionTestExecutionSummary(
            componentVersionId=f"version-{i}",
            instanceArchitecture=GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
            instanceId=GlobalVariables.TEST_INSTANCE_ID.value,
            instanceImageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
            instanceOsVersion=GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
            instancePlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            status=component_version_test_execution.ComponentVersionTestExecutionCommandStatus.Success,
            testExecutionId=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        for i in range(2)
    ]

    test_executions_domain_query_service_mock.get_component_version_test_execution_logs_url.return_value = (
        GlobalVariables.TEST_S3_LOG_PRESIGNED_URL.value
    )

    return test_executions_domain_query_service_mock


@pytest.fixture
def mocked_mandatory_components_list_domain_query_service(
    get_mock_mandatory_components_list,
) -> mandatory_components_list_domain_query_service.MandatoryComponentsListDomainQueryService:
    mandatory_components_list_domain_query_service_mock = mock.create_autospec(
        spec=mandatory_components_list_domain_query_service.MandatoryComponentsListDomainQueryService,
    )
    mandatory_components_list_domain_query_service_mock.get_mandatory_components_list.return_value = (
        get_mock_mandatory_components_list()
    )
    mandatory_components_lists = list()
    mandatory_components_lists.append(get_mock_mandatory_components_list())
    mandatory_component_list_object = get_mock_mandatory_components_list()
    mandatory_component_list_object.mandatoryComponentsListPlatform = "Windows"
    mandatory_component_list_object.mandatoryComponentsListOsVersion = "Microsoft Windows Server 2025"
    mandatory_components_lists.append(mandatory_component_list_object)
    mandatory_components_list_domain_query_service_mock.get_mandatory_components_lists.return_value = (
        mandatory_components_lists
    )
    return mandatory_components_list_domain_query_service_mock


@pytest.fixture
def mocked_pipeline_domain_query_service() -> pipeline_domain_query_service.PipelineDomainQueryService:
    pipeline_domain_query_service_mock = mock.create_autospec(
        spec=pipeline_domain_query_service.PipelineDomainQueryService
    )

    pipeline_domain_query_service_mock.get_pipelines.return_value = [
        pipeline.Pipeline(
            projectId=GlobalVariables.TEST_PROJECT_ID.value,
            pipelineId=f"pipe-{i}",
            buildInstanceTypes=list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value),
            pipelineDescription=GlobalVariables.TEST_PIPELINE_DESCRIPTION.value,
            pipelineName=GlobalVariables.TEST_PIPELINE_NAME.value,
            pipelineSchedule=GlobalVariables.TEST_PIPELINE_SCHEDULE.value,
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
            recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
            status=pipeline.PipelineStatus.Created,
            distributionConfigArn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
            infrastructureConfigArn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
            pipelineArn=GlobalVariables.TEST_PIPELINE_PIPELINE_ARN.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATED_BY.value,
        )
        for i in range(2)
    ]
    pipeline_domain_query_service_mock.get_pipeline.return_value = pipeline.Pipeline(
        projectId=GlobalVariables.TEST_PROJECT_ID.value,
        pipelineId=GlobalVariables.TEST_PIPELINE_ID.value,
        buildInstanceTypes=list(GlobalVariables.TEST_PIPELINE_BUILD_INSTANCE_TYPES.value),
        pipelineDescription=GlobalVariables.TEST_PIPELINE_DESCRIPTION.value,
        pipelineName=GlobalVariables.TEST_PIPELINE_NAME.value,
        pipelineSchedule=GlobalVariables.TEST_PIPELINE_SCHEDULE.value,
        recipeId=GlobalVariables.TEST_RECIPE_ID.value,
        recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
        recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
        status=pipeline.PipelineStatus.Created,
        distributionConfigArn=GlobalVariables.TEST_PIPELINE_DISTRIBUTION_CONFIG_ARN.value,
        infrastructureConfigArn=GlobalVariables.TEST_PIPELINE_INFRASTRUCTURE_CONFIG_ARN.value,
        pipelineArn=GlobalVariables.TEST_PIPELINE_PIPELINE_ARN.value,
        createDate=GlobalVariables.TEST_CREATE_DATE.value,
        createdBy=GlobalVariables.TEST_CREATED_BY.value,
        lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATED_BY.value,
    )

    return pipeline_domain_query_service_mock


@pytest.fixture
def mocked_recipe_domain_query_service() -> recipe_domain_query_service.RecipeDomainQueryService:
    recipe_domain_query_service_mock = mock.create_autospec(spec=recipe_domain_query_service.RecipeDomainQueryService)

    recipe_domain_query_service_mock.get_recipes.return_value = [
        recipe.Recipe(
            projectId=GlobalVariables.TEST_PROJECT_ID.value,
            recipeId=f"reci-{i}",
            recipeDescription=GlobalVariables.TEST_RECIPE_DESCRIPTION.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipePlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            recipeArchitecture=GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
            recipeOsVersion=GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
            status=recipe.RecipeStatus.Created,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        for i in range(2)
    ]

    recipe_domain_query_service_mock.get_recipe.return_value = recipe.Recipe(
        projectId=GlobalVariables.TEST_PROJECT_ID.value,
        recipeId=GlobalVariables.TEST_RECIPE_ID.value,
        recipeDescription=GlobalVariables.TEST_RECIPE_DESCRIPTION.value,
        recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
        recipePlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
        recipeArchitecture=GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
        recipeOsVersion=GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
        status=recipe.RecipeStatus.Created,
        createDate=GlobalVariables.TEST_CREATE_DATE.value,
        createdBy=GlobalVariables.TEST_CREATED_BY.value,
        lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
    )

    return recipe_domain_query_service_mock


@pytest.fixture
def mocked_recipe_versions_domain_query_service() -> (
    recipe_version_domain_query_service.RecipeVersionDomainQueryService
):
    recipe_versions_domain_query_service_mock = mock.create_autospec(
        spec=recipe_version_domain_query_service.RecipeVersionDomainQueryService
    )

    recipe_versions_domain_query_service_mock.get_latest_recipe_version_name.return_value = "1.1.0-rc.1"
    recipe_versions_domain_query_service_mock.get_recipe_versions.return_value = [
        recipe_version.RecipeVersion(
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeVersionId=f"version-{i}",
            recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipeVersionDescription=GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
            recipeComponentsVersions=[
                component_version_entry.ComponentVersionEntry(
                    componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                    componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                    componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                    componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                    componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                    order=1,
                )
            ],
            parentImageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
            recipeVersionVolumeSize=GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
            status=recipe_version.RecipeVersionStatus.Creating,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            createdBy=GlobalVariables.TEST_CREATED_BY.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
            lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        for i in range(2)
    ]
    recipe_versions_domain_query_service_mock.get_recipe_version.return_value = recipe_version.RecipeVersion(
        recipeId=GlobalVariables.TEST_RECIPE_ID.value,
        recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
        recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
        recipeVersionDescription=GlobalVariables.TEST_RECIPE_VERSION_DESCRIPTION.value,
        recipeComponentsVersions=[
            component_version_entry.ComponentVersionEntry(
                componentId=GlobalVariables.TEST_COMPONENT_ID.value,
                componentName=GlobalVariables.TEST_COMPONENT_NAME.value,
                componentVersionId=GlobalVariables.TEST_COMPONENT_VERSION_ID.value,
                componentVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
                componentVersionType=GlobalVariables.TEST_COMPONENT_VERSION_TYPE.value,
                order=1,
            )
        ],
        parentImageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
        recipeVersionVolumeSize=GlobalVariables.TEST_RECIPE_VERSION_VOLUME_SIZE.value,
        status=recipe_version.RecipeVersionStatus.Creating,
        createDate=GlobalVariables.TEST_CREATE_DATE.value,
        createdBy=GlobalVariables.TEST_CREATED_BY.value,
        lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        lastUpdatedBy=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
    )

    recipe_versions_summary_list = list()
    for i in range(2):
        for j in range(3):
            recipe_versions_summary_list.append(
                recipe_version_summary.RecipeVersionSummary(
                    recipeId=f"reci-{i}",
                    recipeVersionId=f"vers-{i}-{j}",
                    recipeVersionName=GlobalVariables.TEST_RECIPE_VERSION_NAME.value,
                    recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
                )
            )
    recipe_versions_domain_query_service_mock.get_all_recipes_versions.return_value = recipe_versions_summary_list

    return recipe_versions_domain_query_service_mock


@pytest.fixture
def mocked_recipe_test_executions_domain_query_service() -> (
    recipe_version_test_execution_domain_query_service.RecipeVersionTestExecutionDomainQueryService
):
    test_recipe_executions_domain_query_service_mock = mock.create_autospec(
        spec=recipe_version_test_execution_domain_query_service.RecipeVersionTestExecutionDomainQueryService,
    )

    test_recipe_executions_domain_query_service_mock.get_recipe_version_test_execution_summaries.return_value = [
        recipe_version_test_execution_summary.RecipeVersionTestExecutionSummary(
            recipeVersionId=f"version-{i}",
            instanceArchitecture=GlobalVariables.TEST_COMPONENT_SUPPORTED_ARCHITECTURES.value[0],
            instanceImageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
            instanceOsVersion=GlobalVariables.TEST_COMPONENT_SUPPORTED_OS_VERSIONS.value[0],
            instancePlatform=GlobalVariables.TEST_COMPONENT_PLATFORM.value,
            status=recipe_version_test_execution.RecipeVersionTestExecutionCommandStatus.Success,
            testExecutionId=GlobalVariables.TEST_TEST_EXECUTION_ID.value,
            instanceId=GlobalVariables.TEST_INSTANCE_ID.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
        for i in range(2)
    ]

    test_recipe_executions_domain_query_service_mock.get_recipe_version_test_execution_logs_url.return_value = (
        GlobalVariables.TEST_S3_LOG_PRESIGNED_URL.value
    )

    return test_recipe_executions_domain_query_service_mock


@pytest.fixture
def mocked_image_domain_query_service() -> image_domain_query_service.ImageDomainQueryService:
    image_domain_query_service_mock = mock.create_autospec(spec=image_domain_query_service.ImageDomainQueryService)
    image_domain_query_service_mock.get_images.return_value = [
        image.Image(
            projectId=GlobalVariables.TEST_PROJECT_ID.value,
            imageId=GlobalVariables.TEST_IMAGE_ID.value,
            imageBuildVersion=GlobalVariables.TEST_IMAGE_BUILD_VERSION.value,
            imageBuildVersionArn=GlobalVariables.TEST_IMAGE_BUILD_VERSION_ARN.value,
            pipelineId=GlobalVariables.TEST_PIPELINE_ID.value,
            pipelineName=GlobalVariables.TEST_PIPELINE_NAME.value,
            recipeId=GlobalVariables.TEST_RECIPE_ID.value,
            recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
            recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
            recipeVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
            status=image.ImageStatus.Created,
            imageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
            createDate=GlobalVariables.TEST_CREATE_DATE.value,
            lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
        )
    ]

    image_domain_query_service_mock.get_image.return_value = image.Image(
        projectId=GlobalVariables.TEST_PROJECT_ID.value,
        imageId=GlobalVariables.TEST_IMAGE_ID.value,
        imageBuildVersion=GlobalVariables.TEST_IMAGE_BUILD_VERSION.value,
        imageBuildVersionArn=GlobalVariables.TEST_IMAGE_BUILD_VERSION_ARN.value,
        pipelineId=GlobalVariables.TEST_PIPELINE_ID.value,
        pipelineName=GlobalVariables.TEST_PIPELINE_NAME.value,
        recipeId=GlobalVariables.TEST_RECIPE_ID.value,
        recipeName=GlobalVariables.TEST_RECIPE_NAME.value,
        recipeVersionId=GlobalVariables.TEST_RECIPE_VERSION_ID.value,
        recipeVersionName=GlobalVariables.TEST_COMPONENT_VERSION_NAME.value,
        status=image.ImageStatus.Created,
        imageUpstreamId=GlobalVariables.TEST_IMAGE_UPSTREAM_ID.value,
        createDate=GlobalVariables.TEST_CREATE_DATE.value,
        lastUpdateDate=GlobalVariables.TEST_LAST_UPDATE_DATE.value,
    )
    return image_domain_query_service_mock


@pytest.fixture
def mocked_create_component_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_archive_component_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_share_component_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_update_component_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_create_component_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_release_component_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_update_component_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_retire_component_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_create_mandatory_components_list_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_update_mandatory_components_list_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_create_recipe_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_archive_recipe_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_create_recipe_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_retire_recipe_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_update_recipe_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_release_recipe_version_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_image_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_create_pipeline_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_retire_pipeline_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_update_pipeline_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_create_image_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_generate_component_definition_cmd_handler():
    return mock.MagicMock()


@pytest.fixture
def mocked_get_generation_component_definition_status_cmd_handler():
    return mock.MagicMock()


@pytest.fixture()
def mocked_image_query_service() -> ec2_image_builder_pipeline_service.Ec2ImageBuilderPipelineService:
    image_query_service_mock = mock.create_autospec(
        spec=ec2_image_builder_pipeline_service.Ec2ImageBuilderPipelineService
    )
    image_query_service_mock.get_pipeline_allowed_build_instance_types.return_value = [
        "m8a.2xlarge",
        "m8i.2xlarge",
        "m8a.4xlarge",
        "m8i.4xlarge",
    ]

    return image_query_service_mock


@pytest.fixture
def mocked_dependencies(
    mocked_create_component_cmd_handler,
    mocked_archive_component_cmd_handler,
    mocked_share_component_cmd_handler,
    mocked_update_component_cmd_handler,
    mocked_create_component_version_cmd_handler,
    mocked_release_component_version_cmd_handler,
    mocked_update_component_version_cmd_handler,
    mocked_retire_component_version_cmd_handler,
    mocked_create_recipe_cmd_handler,
    mocked_create_recipe_version_cmd_handler,
    mocked_retire_recipe_version_cmd_handler,
    mocked_update_recipe_version_cmd_handler,
    mocked_release_recipe_version_cmd_handler,
    mocked_component_domain_query_service,
    mocked_component_versions_domain_query_service,
    mocked_component_test_executions_domain_query_service,
    mocked_recipe_domain_query_service,
    mocked_archive_recipe_cmd_handler,
    mocked_recipe_versions_domain_query_service,
    mocked_recipe_test_executions_domain_query_service,
    mocked_image_domain_query_service,
    mocked_mandatory_components_list_domain_query_service,
    mocked_create_mandatory_components_list_cmd_handler,
    mocked_update_mandatory_components_list_cmd_handler,
    mocked_create_pipeline_cmd_handler,
    mocked_retire_pipeline_cmd_handler,
    mocked_update_pipeline_cmd_handler,
    mocked_pipeline_domain_query_service,
    mocked_create_image_cmd_handler,
    mocked_image_query_service,
) -> bootstrapper.Dependencies:
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock.MagicMock(),
        )
        .register_handler(
            create_component_command.CreateComponentCommand,
            mocked_create_component_cmd_handler,
        )
        .register_handler(
            archive_component_command.ArchiveComponentCommand,
            mocked_archive_component_cmd_handler,
        )
        .register_handler(
            share_component_command.ShareComponentCommand,
            mocked_share_component_cmd_handler,
        )
        .register_handler(
            update_component_command.UpdateComponentCommand,
            mocked_update_component_cmd_handler,
        )
        .register_handler(
            create_component_version_command.CreateComponentVersionCommand,
            mocked_create_component_version_cmd_handler,
        )
        .register_handler(
            release_component_version_command.ReleaseComponentVersionCommand,
            mocked_release_component_version_cmd_handler,
        )
        .register_handler(
            update_component_version_command.UpdateComponentVersionCommand,
            mocked_update_component_version_cmd_handler,
        )
        .register_handler(
            retire_component_version_command.RetireComponentVersionCommand,
            mocked_retire_component_version_cmd_handler,
        )
        .register_handler(
            create_recipe_command.CreateRecipeCommand,
            mocked_create_recipe_cmd_handler,
        )
        .register_handler(
            archive_recipe_command.ArchiveRecipeCommand,
            mocked_archive_recipe_cmd_handler,
        )
        .register_handler(
            create_recipe_version_command.CreateRecipeVersionCommand,
            mocked_create_recipe_version_cmd_handler,
        )
        .register_handler(
            retire_recipe_version_command.RetireRecipeVersionCommand,
            mocked_retire_recipe_version_cmd_handler,
        )
        .register_handler(
            update_recipe_version_command.UpdateRecipeVersionCommand,
            mocked_update_recipe_version_cmd_handler,
        )
        .register_handler(
            release_recipe_version_command.ReleaseRecipeVersionCommand,
            mocked_release_recipe_version_cmd_handler,
        )
        .register_handler(
            create_mandatory_components_list_command.CreateMandatoryComponentsListCommand,
            mocked_create_mandatory_components_list_cmd_handler,
        )
        .register_handler(
            update_mandatory_components_list_command.UpdateMandatoryComponentsListCommand,
            mocked_update_mandatory_components_list_cmd_handler,
        )
        .register_handler(
            create_pipeline_command.CreatePipelineCommand,
            mocked_create_pipeline_cmd_handler,
        )
        .register_handler(
            retire_pipeline_command.RetirePipelineCommand,
            mocked_retire_pipeline_cmd_handler,
        )
        .register_handler(
            update_pipeline_command.UpdatePipelineCommand,
            mocked_update_pipeline_cmd_handler,
        )
        .register_handler(
            create_image_command.CreateImageCommand,
            mocked_create_image_cmd_handler,
        ),
        component_domain_qry_srv=mocked_component_domain_query_service,
        component_version_domain_qry_srv=mocked_component_versions_domain_query_service,
        component_version_test_execution_domain_qry_srv=mocked_component_test_executions_domain_query_service,
        recipe_domain_qry_srv=mocked_recipe_domain_query_service,
        recipe_version_domain_qry_srv=mocked_recipe_versions_domain_query_service,
        recipe_version_test_execution_domain_qry_srv=mocked_recipe_test_executions_domain_query_service,
        image_domain_qry_srv=mocked_image_domain_query_service,
        mandatory_components_list_domain_qry_srv=mocked_mandatory_components_list_domain_query_service,
        pipeline_domain_qry_srv=mocked_pipeline_domain_query_service,
        pipeline_srv=mocked_image_query_service,
        component_definition_service=mock.create_autospec(
            spec=aws_component_definition_service.AWSComponentDefinitionService,
            instance=True,
        ),
    )
