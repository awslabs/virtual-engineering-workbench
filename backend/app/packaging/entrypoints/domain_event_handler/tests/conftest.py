import json
import logging
from unittest import mock

import boto3
import moto
import pytest
from attr import dataclass

from app.packaging.domain.commands.component import (
    deploy_component_version_command,
    remove_component_version_command,
    update_component_version_associations_command,
)
from app.packaging.domain.commands.pipeline import (
    deploy_pipeline_command,
    remove_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    deploy_recipe_version_command,
    remove_recipe_version_command,
    update_recipe_version_associations_command,
    update_recipe_version_on_component_update_command,
)
from app.packaging.domain.model.shared import component_version_entry
from app.packaging.entrypoints.domain_event_handler import bootstrapper
from app.shared.adapters.message_bus import in_memory_command_bus


@pytest.fixture()
def global_variables():
    _global_variables = {
        "TEST_AMI_FACTORY_VPC_NAME": "vpc-test",
        "TEST_AMI_ID": "ami-01234567890abcdef",
        "TEST_ARCHITECTURE": "amd64",
        "TEST_GSI_NAME_ENTITIES": "gsi_entities",
        "TEST_GSI_NAME_CUSTOM_QUERY_BY_STATUS": "gsi_custom_query_by_status_key",
        "TEST_GSI_NAME_INVERTED_PK": "gsi_inverted_primary_key",
        "TEST_IMAGE_KEY_NAME": "test-key",
        "TEST_IMAGE_ID": "imag-12345abc",
        "TEST_INSTANCE_ID": "i-01234567890abcdef",
        "TEST_INSTANCE_PROFILE_NAME": "instance-profile-test",
        "TEST_INSTANCE_ROLE_NAME": "role-test",
        "TEST_INSTANCE_SECURITY_GROUP_NAME": "sg-test",
        "TEST_INSTANCE_TYPE": "m8i.2xlarge",
        "TEST_OS_VERSION": "Ubuntu 24",
        "TEST_PLATFORM": "Linux",
        "TEST_PROJECT_ID": "proj-12345",
        "TEST_RECIPE_ID": "reci-1234abcd",
        "TEST_RECIPE_VERSION_ID": "vers-1234abcd",
        "TEST_RECIPE_VERSION_NAME": "1.0.0",
        "TEST_RECIPE_VERSION_VOLUME_SIZE": "8",
        "TEST_REGION": "us-east-1",
        "TEST_TABLE_NAME": "test-table",
        "TEST_VOLUME_SIZE": 500,
        "DEFAULT_PAGE_SIZE": 50,
        "TEST_COMPONENT_ID": "comp-1",
        "TEST_COMPONENT_VERSION_ID": "version-1",
        "TEST_COMPONENT_VERSION_NAME": "1.0.0",
        "TEST_TEST_EXECUTION_ID": "c0220642-ced2-4f46-bea3-1601a70b5c55",
        "TEST_BUCKET_NAME": "fake-bucket",
        "FAKE_BUCKET": {"Bucket": "fake-bucket"},
        "DDB_TABLE_DEFINITION": {
            "TableName": "test-table",
            "KeySchema": [
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "entity", "AttributeType": "S"},
            ],
            "BillingMode": "PAY_PER_REQUEST",
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "gsi_inverted_primary_key",
                    "KeySchema": [
                        {"AttributeName": "SK", "KeyType": "HASH"},
                        {"AttributeName": "PK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "KEYS_ONLY"},
                },
                {
                    "IndexName": "gsi_entities",
                    "KeySchema": [
                        {"AttributeName": "entity", "KeyType": "HASH"},
                        {"AttributeName": "SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        },
        "TEST_AMI_FACTORY_SUBNET_NAMES": "subnet-1a,subnet-1b",
    }

    yield _global_variables


@pytest.fixture
def mock_dynamodb(global_variables):
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name=global_variables.get("TEST_REGION"))


@pytest.fixture(autouse=True)
def backend_app_dynamodb_table(mock_dynamodb, global_variables):
    table = mock_dynamodb.create_table(**global_variables.get("DDB_TABLE_DEFINITION"))

    table.meta.client.get_waiter("table_exists").wait(TableName=global_variables.get("TEST_TABLE_NAME"))

    return table


@pytest.fixture(autouse=True)
def lambda_env_vars(monkeypatch, mock_event_bus, global_variables):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("TABLE_NAME", global_variables.get("TEST_TABLE_NAME"))
    monkeypatch.setenv("GSI_NAME_ENTITIES", global_variables.get("TEST_GSI_NAME_ENTITIES"))
    monkeypatch.setenv("GSI_NAME_INVERTED_PK", global_variables.get("TEST_GSI_NAME_INVERTED_PK"))
    monkeypatch.setenv("DOMAIN_EVENT_BUS_ARN", mock_event_bus.get("EventBusArn"))
    monkeypatch.setenv("BOUNDED_CONTEXT", "packaging.bc.test")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("AWS_DEFAULT_REGION", global_variables.get("TEST_REGION"))
    monkeypatch.setenv("COMPONENT_S3_BUCKET_NAME", global_variables.get("TEST_BUCKET_NAME"))
    monkeypatch.setenv("AMI_FACTORY_AWS_ACCOUNT_ID", "001234567890")
    monkeypatch.setenv("ADMIN_ROLE", "AdminRole")
    monkeypatch.setenv(
        "AMI_FACTORY_SUBNET_NAMES",
        global_variables.get("TEST_AMI_FACTORY_SUBNET_NAMES"),
    )
    monkeypatch.setenv("AMI_FACTORY_VPC_NAME", "vpc-test")
    monkeypatch.setenv("AUDIT_LOGGING_KEY_NAME", "test-key")
    monkeypatch.setenv("GSI_CUSTOM_STATUS_KEY", "gsi_custom_query_by_status_key")
    monkeypatch.setenv("IMAGE_KEY_NAME", "test-key")
    monkeypatch.setenv("INSTANCE_PROFILE_NAME", "instance-profile-test")
    monkeypatch.setenv("INSTANCE_SECURITY_GROUP_NAME", "sg-test")
    monkeypatch.setenv("RECIPE_S3_BUCKET_NAME", "fake-recipe-bucket")
    monkeypatch.setenv("SYSTEM_CONFIGURATION_MAPPING_PARAM_NAME", "/test/system/param")
    monkeypatch.setenv("TOPIC_NAME", "test-topic")


@pytest.fixture()
def mock_events_client(global_variables):
    with moto.mock_aws():
        yield boto3.client("events", global_variables.get("TEST_REGION"))


@pytest.fixture(autouse=True)
def mock_event_bus(mock_events_client):
    return mock_events_client.create_event_bus(Name="test-eb")


@pytest.fixture()
def mock_s3_client(global_variables):
    with moto.mock_aws():
        yield boto3.client("s3", global_variables.get("TEST_REGION"))


@pytest.fixture(autouse=True)
def mock_s3_bucket(mock_s3_client, global_variables):
    mock_s3_client.create_bucket(**global_variables.get("FAKE_BUCKET"))


@pytest.fixture(autouse=True)
def mock_sts_client(global_variables):
    with moto.mock_aws():
        yield boto3.client("sts", global_variables.get("TEST_REGION"))


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch, global_variables):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCOUNT", "123456789012")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "Test")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "PackagingEvents")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv(
        "DOMAIN_EVENT_BUS_ARN",
        "arn:aws:events:us-east-1:001234567890:event-bus/packaging-events",
    )
    monkeypatch.setenv("BOUNDED_CONTEXT", "Packaging")
    monkeypatch.setenv("ADMIN_ROLE", "Admin")
    monkeypatch.setenv("AMI_FACTORY_AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("PIPELINES_CONFIGURATION_MAPPING_PARAM_NAME", "/test/pipelines/param")
    monkeypatch.setenv(
        "AMI_FACTORY_SUBNET_NAMES",
        global_variables.get("TEST_AMI_FACTORY_SUBNET_NAMES"),
    )


@pytest.fixture(autouse=True)
def ssm_mock():
    with moto.mock_aws():
        yield boto3.client(
            "ssm",
            region_name="us-east-1",
            aws_access_key_id="access-key-id",
            aws_secret_access_key="secret-access-key",
            aws_session_token="session-token",
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
def mock_ai_system_prompt_parameter(ssm_mock):
    ssm_mock.put_parameter(
        Name="/test/shared/ai-system-prompt",
        Type="String",
        Value="Test AI system prompt for EC2 Image Builder component generation.",
    )


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
def generate_event():
    def _generate_event(detail_type: str, detail: dict):
        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": detail_type,
            "source": "org.workbench.projects.dev",
            "account": "123456789012",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": [],
            "detail": detail,
        }

    return _generate_event


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


@pytest.fixture
def component_version_creation_started_event_payload(
    get_test_component_yaml_definition,
):
    return {
        "eventName": "ComponentVersionCreationStarted",
        "componentId": "comp-1234abcd",
        "componentVersionId": "vers-1234abcd",
        "componentVersionName": "1.0.0-rc.1",
        "componentVersionDescription": "Test description",
        "componentVersionYamlDefinition": get_test_component_yaml_definition(),
        "softwareVendor": "vector",
        "softwareVersion": "1.0.0",
        "licenseDashboard": "https://proserve.license.com/index.php?action=dashboard.view&dashboardid=1",
        "notes": "This is a test component software version.",
        "componentVersionDependencies": [
            {
                "componentId": "comp-1234efgh",
                "componentName": "test-component-1234efgh",
                "componentVersionId": "vers-1234efgh",
                "componentVersionName": "1.0.0",
                "order": 1,
            },
        ],
    }


@pytest.fixture
def component_version_update_started_event_payload(get_test_component_yaml_definition):
    return {
        "eventName": "ComponentVersionUpdateStarted",
        "componentId": "comp-1234abcd",
        "componentVersionId": "vers-1234abcd",
        "componentVersionName": "1.0.0-rc.1",
        "componentVersionDescription": "Test description",
        "componentVersionDependencies": [
            {
                "componentId": "comp-1234ijkl",
                "componentName": "test-component-1234ijkl",
                "componentVersionId": "vers-1234ijkl",
                "componentVersionName": "1.0.0",
                "order": 1,
            },
        ],
        "previousComponentVersionDependencies": [
            {
                "componentId": "comp-1234efgh",
                "componentName": "test-component-1234efgh",
                "componentVersionId": "vers-1234efgh",
                "componentVersionName": "1.0.0",
                "order": 1,
            },
        ],
        "componentVersionYamlDefinition": get_test_component_yaml_definition(),
    }


@pytest.fixture
def recipe_version_retirement_started_payload():
    return {
        "eventName": "RecipeVersionRetirementStarted",
        "projectId": "proj-12345",
        "recipeId": "reci-1234abcd",
        "recipeName": "test-recipe",
        "recipeVersionId": "vers-1234abcd",
        "recipeVersionArn": "arn:aws:imagebuilder:us-east-1:123456789012:image-recipe/test-recipe/1.0.0",
        "recipeVersionComponentArn": "arn:aws:imagebuilder:us-east-1:123456789012:component/test-recipe/1.0.0/1",
        "recipeComponentsVersions": [
            {
                "componentId": "comp-1234efgh",
                "componentName": "test-component-1234efgh",
                "componentVersionId": "vers-1234efgh",
                "componentVersionName": "1.0.0",
                "order": 1,
            },
        ],
        "recipeVersionName": "1.0.0",
        "lastUpdatedBy": "T100000",
    }


@pytest.fixture
def component_version_retirement_started_payload():
    return {
        "eventName": "ComponentVersionRetirementStarted",
        "componentId": "comp-1234abcd",
        "componentVersionId": "vers-1234abcd",
        "componentBuildVersionArn": "arn:aws:imagebuilder:us-east-1:123456789012:component/test-component/1.0.0/1",
        "componentVersionDependencies": [
            {
                "componentId": "comp-1234efgh",
                "componentName": "test-component-1234efgh",
                "componentVersionId": "vers-1234efgh",
                "componentVersionName": "1.0.0",
                "order": 1,
            },
        ],
    }


@pytest.fixture
def component_version_release_completed_event_payload():
    return {
        "eventName": "ComponentVersionReleaseCompleted",
        "componentId": "comp-1234abcd",
        "componentVersionId": "vers-1234abcd",
        "componentVersionDependencies": [
            {
                "componentId": "comp-1234efgh",
                "componentName": "test-component-1234efgh",
                "componentVersionId": "vers-1234efgh",
                "componentVersionName": "1.0.0",
                "order": 1,
            },
        ],
    }


@pytest.fixture
def recipe_version_creation_started_event_payload():
    return {
        "eventName": "RecipeVersionCreationStarted",
        "projectId": "proj-12345",
        "recipeId": "reci-1234abc",
        "recipeVersionId": "vers-1234abcd",
        "recipeVersionName": "1.0.0-rc.1",
        "recipeComponentsVersions": [
            {
                "componentId": "comp-1234abc",
                "componentName": "mock-component",
                "componentVersionId": "vers-1234abc",
                "componentVersionName": "1.0.0",
                "componentVersionType": component_version_entry.ComponentVersionEntryType.Main.value,
                "order": 1,
            },
            {
                "componentId": "comp-6789abc",
                "componentName": "mock-component2",
                "componentVersionId": "vers-6789abc",
                "componentVersionName": "2.1.0",
                "componentVersionType": component_version_entry.ComponentVersionEntryType.Main.value,
                "order": 2,
            },
        ],
        "parentImageUpstreamId": "ami-08734ec479a1ace4a",
        "recipeVersionVolumeSize": "8",
    }


@pytest.fixture
def recipe_version_update_started_event_payload():
    return {
        "eventName": "RecipeVersionUpdateStarted",
        "projectId": "proj-12345",
        "recipeId": "reci-1234abc",
        "recipeVersionId": "vers-1234abcd",
        "recipeVersionName": "1.0.0-rc.1",
        "recipeComponentsVersions": [
            {
                "componentId": "comp-1234abc",
                "componentName": "mock-component",
                "componentVersionId": "vers-1234abc",
                "componentVersionName": "1.0.0",
                "componentVersionType": component_version_entry.ComponentVersionEntryType.Main.value,
                "order": 1,
            },
            {
                "componentId": "comp-6789abc",
                "componentName": "mock-component2",
                "componentVersionId": "vers-6789abc",
                "componentVersionName": "2.1.0",
                "componentVersionType": component_version_entry.ComponentVersionEntryType.Main.value,
                "order": 2,
            },
        ],
        "parentImageUpstreamId": "ami-08734ec479a1ace4a",
        "recipeVersionVolumeSize": "8",
    }


@pytest.fixture
def recipe_version_release_completed_event_payload():
    return {
        "eventName": "RecipeVersionReleaseCompleted",
        "recipeId": "reci-1234abc",
        "recipeVersionId": "vers-1234abcd",
        "recipeComponentsVersions": [
            {
                "componentId": "comp-1234abc",
                "componentName": "mock-component",
                "componentVersionId": "vers-1234abc",
                "componentVersionName": "1.0.0",
                "componentVersionType": component_version_entry.ComponentVersionEntryType.Main.value,
                "order": 1,
            },
            {
                "componentId": "comp-6789abc",
                "componentName": "mock-component2",
                "componentVersionId": "vers-6789abc",
                "componentVersionName": "2.1.0",
                "componentVersionType": component_version_entry.ComponentVersionEntryType.Main.value,
                "order": 2,
            },
        ],
    }


@pytest.fixture
def pipeline_creation_started_event_payload():
    return {
        "eventName": "PipelineCreationStarted",
        "projectId": "proj-12345",
        "pipelineId": "pipe-1235abc",
    }


@pytest.fixture
def get_pipeline_retirement_started_event_payload():
    def _get_pipeline_retirement_started_event_payload(
        distribution_config_arn: (
            str | None
        ) = "arn:aws:imagebuilder:us-east-1:123456789012:distribution-configuration/pipe-1235abc",
        infrastructure_config_arn: (
            str | None
        ) = "arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/pipe-1235abc",
        pipeline_arn: str | None = "arn:aws:imagebuilder:us-east-1:123456789012:image-pipeline/pipe-1235abc",
    ) -> dict[str, str]:
        pipeline_retirement_started_event = {
            "eventName": "PipelineRetirementStarted",
            "projectId": "proj-12345",
            "pipelineId": "pipe-1235abc",
        }
        if distribution_config_arn:
            pipeline_retirement_started_event["distributionConfigArn"] = distribution_config_arn
        if infrastructure_config_arn:
            pipeline_retirement_started_event["infrastructureConfigArn"] = infrastructure_config_arn
        if pipeline_arn:
            pipeline_retirement_started_event["pipelineArn"] = pipeline_arn

        return pipeline_retirement_started_event

    return _get_pipeline_retirement_started_event_payload


@pytest.fixture
def pipeline_update_started_event_payload():
    return {
        "eventName": "PipelineUpdateStarted",
        "projectId": "proj-12345",
        "pipelineId": "pipe-1235abc",
    }


@pytest.fixture
def recipe_version_update_on_component_update_requested_event_payload():
    return {
        "eventName": "RecipeVersionUpdateOnComponentUpdateRequested",
        "componentId": "comp-12345",
        "componentVersionId": "vers-12345",
        "last_updated_by": "T100000",
    }


@pytest.fixture()
def mock_logger():
    yield mock.create_autospec(spec=logging.Logger, instance=True)


@pytest.fixture
def mock_deploy_component_version_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_remove_recipe_version_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_remove_component_version_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_deploy_recipe_version_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_deploy_pipeline_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_update_recipe_on_component_update_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_remove_pipeline_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_update_component_version_associations_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_update_recipe_version_associations_command_handler():
    return mock.Mock()


@pytest.fixture
def mock_component_definition_service():
    from app.packaging.domain.ports import component_version_definition_service

    return mock.Mock(spec=component_version_definition_service.ComponentVersionDefinitionService)


@pytest.fixture
def mock_dependencies(
    mock_deploy_component_version_command_handler,
    mock_logger,
    mock_remove_recipe_version_command_handler,
    mock_remove_component_version_command_handler,
    mock_deploy_recipe_version_command_handler,
    mock_deploy_pipeline_command_handler,
    mock_remove_pipeline_command_handler,
    mock_update_component_version_associations_command_handler,
    mock_update_recipe_version_associations_command_handler,
    mock_update_recipe_on_component_update_command_handler,
    mock_component_definition_service,
):
    return bootstrapper.Dependencies(
        command_bus=in_memory_command_bus.InMemoryCommandBus(
            logger=mock_logger,
        )
        .register_handler(
            deploy_component_version_command.DeployComponentVersionCommand,
            mock_deploy_component_version_command_handler,
        )
        .register_handler(
            remove_recipe_version_command.RemoveRecipeVersionCommand,
            mock_remove_recipe_version_command_handler,
        )
        .register_handler(
            remove_component_version_command.RemoveComponentVersionCommand,
            mock_remove_component_version_command_handler,
        )
        .register_handler(
            deploy_recipe_version_command.DeployRecipeVersionCommand,
            mock_deploy_recipe_version_command_handler,
        )
        .register_handler(
            deploy_pipeline_command.DeployPipelineCommand,
            mock_deploy_pipeline_command_handler,
        )
        .register_handler(
            remove_pipeline_command.RemovePipelineCommand,
            mock_remove_pipeline_command_handler,
        )
        .register_handler(
            update_component_version_associations_command.UpdateComponentVersionAssociationsCommand,
            mock_update_component_version_associations_command_handler,
        )
        .register_handler(
            update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand,
            mock_update_recipe_version_associations_command_handler,
        )
        .register_handler(
            update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand,
            mock_update_recipe_on_component_update_command_handler,
        ),
        component_definition_service=mock_component_definition_service,
    )
