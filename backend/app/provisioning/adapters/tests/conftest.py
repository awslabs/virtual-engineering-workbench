import logging
import unittest.mock

import boto3
import botocore
import moto
import pytest
from botocore.exceptions import ClientError
from mypy_boto3_ecs import client as ecs_client

from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.domain.model import (
    product_status,
    provisioned_product,
    provisioning_parameter,
)
from app.provisioning.domain.read_models import component_version_detail, version
from app.shared.adapters.boto.boto_provider import BotoProvider, BotoProviderOptions
from app.shared.adapters.boto.dict_context_provider import DictCtxProvider
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work

orig = botocore.client.BaseClient._make_api_call

GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
GSI_NAME_CUSTOM_QUERY_BY_SC_ID = "gsi_custom_query_by_sc_id"
GSI_NAME_CUSTOM_QUERY_BY_USER_ID = "gsi_custom_query_by_user_id"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2 = "gsi_custom_query_by_alternative_key_2"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3 = "gsi_custom_query_by_alternative_keys_3"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4 = "gsi_custom_query_by_alternative_keys_4"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5 = "gsi_custom_query_by_alternative_keys_5"
TEST_TABLE_NAME = "test-table"
GSI_NAME_ENTITIES = "gsi_entities"
TEST_REGION = "us-east-1"
TEST_OS_VERSION = "Ubuntu 24"
TEST_COMPONENT_VERSION_DETAILS = [
    component_version_detail.ComponentVersionDetail(
        componentName="VS Code",
        componentVersionType=component_version_detail.ComponentVersionEntryType.Main,
        softwareVendor="Microsoft",
        softwareVersion="1.87.0",
    )
]


@pytest.fixture()
def required_env_vars(monkeypatch):
    """Mocked AWS Credentials for moto."""

    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")


@pytest.fixture
def mock_dynamodb(required_env_vars):
    with moto.mock_aws():
        yield boto3.resource("dynamodb", region_name="eu-central-1")


@pytest.fixture()
def provider(mock_logger):
    ctx = DictCtxProvider()
    return BotoProvider(
        ctx,
        mock_logger,
        default_options=BotoProviderOptions(
            aws_role_name="TestRole",
            aws_session_name="TestSession",
        ),
    )


@pytest.fixture
def mock_cloudwatch(required_env_vars, provider):
    with moto.mock_aws():
        yield provider.client("cloudwatch")(BotoProviderOptions(aws_account_id="012345678900", aws_region="us-east-1"))


@pytest.fixture()
def backend_app_dynamodb_table(mock_dynamodb):
    table = mock_dynamodb.create_table(
        TableName=TEST_TABLE_NAME,
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

    table.meta.client.get_waiter("table_exists").wait(TableName=TEST_TABLE_NAME)
    return table


@pytest.fixture()
def mock_table_name():
    return TEST_TABLE_NAME


@pytest.fixture()
def mock_gsi_inverted():
    return GSI_NAME_INVERTED_PK


@pytest.fixture()
def mock_gsi_by_sc_id():
    return GSI_NAME_CUSTOM_QUERY_BY_SC_ID


@pytest.fixture()
def mock_gsi_by_user_id():
    return GSI_NAME_CUSTOM_QUERY_BY_USER_ID


@pytest.fixture()
def mock_gsi_by_entity():
    return GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2


@pytest.fixture()
def mock_gsi_by_product_id():
    return GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3


@pytest.fixture()
def mock_gsi_by_project_id():
    return GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4


@pytest.fixture()
def mock_gsi_by_status():
    return GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5


@pytest.fixture()
def mock_logger():
    return unittest.mock.create_autospec(spec=logging.Logger)


@pytest.fixture()
def mock_ddb_repo(mock_logger, mock_table_name, mock_dynamodb, backend_app_dynamodb_table):
    return dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=mock_table_name,
        dynamodb_client=mock_dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=mock_table_name).repo_factories(),
        logger=mock_logger,
    )


@pytest.fixture()
def mock_moto_error_calls(mock_get_ec2_instance_recommendations_error_request):
    invocations = {"GetEC2InstanceRecommendations": mock_get_ec2_instance_recommendations_error_request}

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with unittest.mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mock_moto_calls(
    mock_provision_product_request,
    mock_list_launch_paths_request,
    mock_describe_provisioned_product_request,
    mock_describe_record_request,
    mock_describe_stacks_request,
    mock_search_provisioned_products,
    mock_terminate_provisioned_product_request,
    mock_get_ec2_instance_recommendations_request,
    mock_update_provisioned_product_request,
    mock_get_connection_status_request,
    mock_start_ec2_instance_request,
    mock_get_template_summary_request,
    mock_describe_stack_events_request,
    mock_get_metric_data_request,
):
    invocations = {
        "ProvisionProduct": mock_provision_product_request,
        "ListLaunchPaths": mock_list_launch_paths_request,
        "DescribeProvisionedProduct": mock_describe_provisioned_product_request,
        "DescribeRecord": mock_describe_record_request,
        "DescribeStacks": mock_describe_stacks_request,
        "SearchProvisionedProducts": mock_search_provisioned_products,
        "TerminateProvisionedProduct": mock_terminate_provisioned_product_request,
        "GetEC2InstanceRecommendations": mock_get_ec2_instance_recommendations_request,
        "UpdateProvisionedProduct": mock_update_provisioned_product_request,
        "GetConnectionStatus": mock_get_connection_status_request,
        "StartInstances": mock_start_ec2_instance_request,
        "GetTemplateSummary": mock_get_template_summary_request,
        "DescribeStackEvents": mock_describe_stack_events_request,
        "GetMetricData": mock_get_metric_data_request,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with unittest.mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mock_get_metric_data_response():
    return {
        "MetricDataResults": [],
        "NextToken": None,
        "Messages": [],
    }


@pytest.fixture()
def mock_get_metric_data_request(mock_get_metric_data_response):
    return unittest.mock.MagicMock(return_value=mock_get_metric_data_response)


@pytest.fixture()
def mock_provision_product_request(mocked_provision_product_response):
    return unittest.mock.MagicMock(return_value=mocked_provision_product_response)


@pytest.fixture()
def mocked_provision_product_response():
    return {
        "RecordDetail": {
            "RecordId": "string",
            "ProvisionedProductName": "string",
            "Status": "CREATED",
            "CreatedTime": "2023-13-16",
            "UpdatedTime": "2023-13-16",
            "ProvisionedProductType": "string",
            "RecordType": "string",
            "ProvisionedProductId": "pp-123",
            "ProductId": "string",
            "ProvisioningArtifactId": "string",
            "PathId": "string",
            "RecordErrors": [
                {"Code": "string", "Description": "string"},
            ],
            "RecordTags": [
                {"Key": "string", "Value": "string"},
            ],
            "LaunchRoleArn": "string",
        }
    }


@pytest.fixture()
def mocked_get_template_summary_response():
    return {
        "Parameters": [
            {
                "ParameterKey": "InstanceType",
                "DefaultValue": "m6x.small",
                "ParameterType": "string",
                "NoEcho": True,
                "Description": "string",
                "ParameterConstraints": {"AllowedValues": ["m6x.large", "m6x.small"]},
            },
        ],
        "Description": "string",
        "Capabilities": [
            "CAPABILITY_IAM",
        ],
        "CapabilitiesReason": "string",
        "ResourceTypes": [
            "string",
        ],
        "Version": "string",
        "Metadata": "string",
        "DeclaredTransforms": [
            "string",
        ],
        "ResourceIdentifierSummaries": [
            {
                "ResourceType": "string",
                "LogicalResourceIds": [
                    "string",
                ],
                "ResourceIdentifiers": [
                    "string",
                ],
            },
        ],
        "Warnings": {
            "UnrecognizedResourceTypes": [
                "string",
            ]
        },
    }


@pytest.fixture()
def mocked_describe_stack_events_response():
    return {
        "StackEvents": [
            {
                "StackId": "string",
                "EventId": "string",
                "StackName": "test-stack",
                "LogicalResourceId": "Workbench",
                "PhysicalResourceId": "Workbench",
                "ResourceType": "string",
                "Timestamp": "TEST_DATE",
                "ResourceStatus": "CREATE_FAILED",
                "ResourceStatusReason": 'Resource handler returned message: "We currently do not have sufficient c8g.metal-24xl',
                "ResourceProperties": "string",
                "ClientRequestToken": "string",
                "HookType": "string",
                "HookStatus": "HOOK_FAILED",
                "HookStatusReason": "string",
                "HookInvocationPoint": "PRE_PROVISION",
                "HookFailureMode": "FAIL",
                "DetailedStatus": "CONFIGURATION_COMPLETE",
            },
        ],
        "NextToken": "string",
    }


@pytest.fixture()
def mocked_describe_stack_events_missing_remove_signal_response():
    return {
        "StackEvents": [
            {
                "StackId": "string",
                "EventId": "string",
                "StackName": "test-stack",
                "LogicalResourceId": "Workbench",
                "PhysicalResourceId": "Workbench",
                "ResourceType": "string",
                "Timestamp": "TEST_DATE",
                "ResourceStatus": "DELETE_FAILED",
                "ResourceStatusReason": 'Resource handler returned message: "Exceeded attempts to wait"',
                "ResourceProperties": "string",
                "ClientRequestToken": "string",
                "HookType": "string",
                "HookStatus": "HOOK_FAILED",
                "HookStatusReason": "string",
                "HookInvocationPoint": "PRE_PROVISION",
                "HookFailureMode": "FAIL",
                "DetailedStatus": "CONFIGURATION_COMPLETE",
            },
        ],
        "NextToken": "string",
    }


@pytest.fixture()
def mock_get_template_summary_request(mocked_get_template_summary_response):
    return unittest.mock.MagicMock(return_value=mocked_get_template_summary_response)


@pytest.fixture()
def mock_describe_stack_events_request(mocked_describe_stack_events_response):
    return unittest.mock.MagicMock(return_value=mocked_describe_stack_events_response)


@pytest.fixture()
def mock_update_provisioned_product_request(mocked_update_provisioned_product_response):
    return unittest.mock.MagicMock(return_value=mocked_update_provisioned_product_response)


@pytest.fixture()
def mocked_update_provisioned_product_response():
    return {
        "RecordDetail": {
            "RecordId": "string",
            "ProvisionedProductName": "string",
            "Status": "CREATED",
            "CreatedTime": "2022-01-01",
            "UpdatedTime": "2022-01-01",
            "ProvisionedProductType": "string",
            "RecordType": "string",
            "ProvisionedProductId": "string",
            "ProductId": "string",
            "ProvisioningArtifactId": "string",
            "PathId": "string",
            "RecordErrors": [
                {"Code": "string", "Description": "string"},
            ],
            "RecordTags": [
                {"Key": "string", "Value": "string"},
            ],
            "LaunchRoleArn": "string",
        }
    }


@pytest.fixture()
def mock_terminate_provisioned_product_request(
    mocked_terminate_provisioned_product_response,
):
    return unittest.mock.MagicMock(return_value=mocked_terminate_provisioned_product_response)


@pytest.fixture()
def mocked_terminate_provisioned_product_response():
    return {
        "RecordDetail": {
            "RecordId": "string",
            "ProvisionedProductName": "string",
            "Status": "CREATED",
            "CreatedTime": "2022-01-01",
            "UpdatedTime": "2022-01-01",
            "ProvisionedProductType": "string",
            "RecordType": "string",
            "ProvisionedProductId": "string",
            "ProductId": "string",
            "ProvisioningArtifactId": "string",
            "PathId": "string",
            "RecordErrors": [
                {"Code": "string", "Description": "string"},
            ],
            "RecordTags": [
                {"Key": "string", "Value": "string"},
            ],
            "LaunchRoleArn": "string",
        }
    }


@pytest.fixture()
def mock_list_launch_paths_request(mocked_list_launch_paths_response):
    return unittest.mock.MagicMock(return_value=mocked_list_launch_paths_response)


@pytest.fixture()
def mocked_list_launch_paths_response():
    return {
        "LaunchPathSummaries": [
            {
                "Id": "path-1",
                "ConstraintSummaries": [
                    {"Type": "string", "Description": "string"},
                ],
                "Tags": [
                    {"Key": "string", "Value": "string"},
                ],
                "Name": "string",
            },
        ],
        "NextPageToken": "string",
    }


@pytest.fixture()
def mock_describe_provisioned_product_request(
    mocked_describe_provisioned_product_response,
):
    return unittest.mock.MagicMock(return_value=mocked_describe_provisioned_product_response)


@pytest.fixture()
def mocked_describe_provisioned_product_response():
    return {
        "ProvisionedProductDetail": {
            "Name": "string",
            "Arn": "string",
            "Type": "string",
            "Id": "string",
            "Status": "AVAILABLE",
            "StatusMessage": "string",
            "CreatedTime": "2023-12-06",
            "IdempotencyToken": "string",
            "LastRecordId": "string",
            "LastProvisioningRecordId": "rec-123",
            "LastSuccessfulProvisioningRecordId": "string",
            "ProductId": "string",
            "ProvisioningArtifactId": "string",
            "LaunchRoleArn": "string",
        },
        "CloudWatchDashboards": [
            {"Name": "string"},
        ],
    }


@pytest.fixture()
def mock_describe_record_request(mocked_describe_record_response):
    return unittest.mock.MagicMock(return_value=mocked_describe_record_response)


@pytest.fixture()
def mocked_describe_record_response():
    return {
        "RecordDetail": {
            "RecordId": "rec-123",
            "ProvisionedProductName": "string",
            "Status": "CREATED",
            "CreatedTime": "2023-12-06",
            "UpdatedTime": "2023-12-06",
            "ProvisionedProductType": "string",
            "RecordType": "string",
            "ProvisionedProductId": "string",
            "ProductId": "string",
            "ProvisioningArtifactId": "string",
            "PathId": "string",
            "RecordErrors": [
                {"Code": "string", "Description": "string"},
            ],
            "RecordTags": [
                {"Key": "string", "Value": "string"},
            ],
            "LaunchRoleArn": "string",
        },
        "RecordOutputs": [
            {
                "OutputKey": "CloudformationStackARN",
                "OutputValue": "arn:aws:cloudformation:us-east-1:001234567890:stack/sc-prov-prod/aaa",
                "Description": "string",
            },
        ],
        "NextPageToken": "string",
    }


@pytest.fixture()
def mock_describe_stacks_request(mocked_describe_stacks_response):
    return unittest.mock.MagicMock(return_value=mocked_describe_stacks_response)


@pytest.fixture()
def mocked_describe_stacks_response():
    return {
        "Stacks": [
            {
                "StackId": "string",
                "StackName": "string",
                "ChangeSetId": "string",
                "Description": "string",
                "Parameters": [
                    {
                        "ParameterKey": "string",
                        "ParameterValue": "string",
                        "UsePreviousValue": True,
                        "ResolvedValue": "string",
                    },
                ],
                "CreationTime": "2023-12-06",
                "DeletionTime": "2023-12-06",
                "LastUpdatedTime": "2023-12-06",
                "RollbackConfiguration": {
                    "RollbackTriggers": [
                        {"Arn": "string", "Type": "string"},
                    ],
                    "MonitoringTimeInMinutes": 123,
                },
                "StackStatus": "CREATE_COMPLETE",
                "StackStatusReason": "string",
                "DisableRollback": True,
                "NotificationARNs": [
                    "string",
                ],
                "TimeoutInMinutes": 123,
                "Capabilities": [
                    "CAPABILITY_IAM",
                ],
                "Outputs": [
                    {
                        "OutputKey": "CloudformationStackARN",
                        "OutputValue": "string",
                        "Description": "string",
                        "ExportName": "string",
                    },
                    {
                        "OutputKey": "some-output-key",
                        "OutputValue": "some-output-value",
                        "Description": "some-description",
                        "ExportName": "some-export-name",
                    },
                ],
                "RoleARN": "string",
                "Tags": [
                    {"Key": "string", "Value": "string"},
                ],
                "EnableTerminationProtection": True,
                "ParentId": "string",
                "RootId": "string",
                "DriftInformation": {
                    "StackDriftStatus": "DRIFTED",
                    "LastCheckTimestamp": "2023-12-06",
                },
                "RetainExceptOnCreate": True,
            },
        ],
        "NextToken": "string",
    }


@pytest.fixture()
def mock_search_provisioned_products(mocked_search_provisioned_products_response):
    return unittest.mock.MagicMock(return_value=mocked_search_provisioned_products_response)


@pytest.fixture()
def mocked_search_provisioned_products_response():
    return {
        "ProvisionedProducts": [
            {
                "Name": "string",
                "Arn": "arn:aws:cloudformation:us-east-1:12345678900:stack/SC-12345678900-pp-q4qjlwuha5arw/127a13f0-ee78-11ed-9daf-0eee20028ecd",
                "Type": "string",
                "Id": "pp-q4qjlwuha5arw",
                "Status": "AVAILABLE",
                "StatusMessage": "string",
                "CreatedTime": "2023-12-13",
                "IdempotencyToken": "string",
                "LastRecordId": "string",
                "LastProvisioningRecordId": "string",
                "LastSuccessfulProvisioningRecordId": "string",
                "Tags": [
                    {"Key": "key-string", "Value": "value-string"},
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


@pytest.fixture(autouse=True)
def mock_get_workbench_recommendation_response():
    return {
        "instanceRecommendations": [
            {
                "instanceArn": f"arn:aws:ec2:us-east-1:001234567890:instance/i-{i}",
                "accountId": "001234567890",
                "instanceName": "",
                "currentInstanceType": "t3a.2xlarge",
                "finding": "OVER_PROVISIONED",
                "findingReasonCodes": [
                    "CPUOverprovisioned",
                    "NetworkBandwidthOverprovisioned",
                ],
                "utilizationMetrics": [
                    {
                        "name": "CPU",
                        "statistic": "MAXIMUM",
                        "value": 16.813333333333333,
                    },
                ],
                "lookBackPeriodInDays": 14.0,
                "recommendationOptions": [
                    {
                        "instanceType": "r6a.xlarge",
                        "projectedUtilizationMetrics": [
                            {
                                "name": "CPU",
                                "statistic": "MAXIMUM",
                                "value": 19.85712643678161,
                            }
                        ],
                        "platformDifferences": [],
                        "performanceRisk": 1.0,
                        "rank": 1,
                        "savingsOpportunity": {
                            "savingsOpportunityPercentage": 24.60106382978723,
                            "estimatedMonthlySavings": {
                                "currency": "USD",
                                "value": 43.10091280160715,
                            },
                        },
                        "migrationEffort": "VeryLow",
                    }
                ],
                "recommendationSources": [
                    {
                        "recommendationSourceArn": "arn:aws:ec2:us-east-1:001234567890:instance/i-0e64ca01e684dc8d6",
                        "recommendationSourceType": "Ec2Instance",
                    }
                ],
                "lastRefreshTimestamp": "2024-01-16T08:30:06.593000+01:00",
                "effectiveRecommendationPreferences": {
                    "cpuVendorArchitectures": ["CURRENT"],
                    "enhancedInfrastructureMetrics": "Inactive",
                    "inferredWorkloadTypes": "Active",
                },
                "inferredWorkloadTypes": [],
                "instanceState": "stopped",
                "tags": [],
                "externalMetricStatus": {
                    "statusCode": "NO_EXTERNAL_METRIC_SET",
                    "statusReason": "You haven't configured an external metrics provider in Compute Optimizer.",
                },
            }
            for i in range(3)
        ],
        "errors": [],
        "nextToken": "mock-token",
    }


@pytest.fixture(autouse=True)
def mock_next_get_workbench_recommendation_response():
    return {
        "instanceRecommendations": [
            {
                "instanceArn": f"arn:aws:ec2:us-east-1:001234567890:instance/i-{i}",
                "accountId": "001234567890",
                "currentInstanceType": "t3a.2xlarge",
                "finding": "OVER_PROVISIONED",
                "lookBackPeriodInDays": 14.0,
                "recommendationOptions": [
                    {
                        "instanceType": "r6a.xlarge",
                        "projectedUtilizationMetrics": [
                            {
                                "name": "CPU",
                                "statistic": "MAXIMUM",
                                "value": 19.85712643678161,
                            }
                        ],
                        "rank": 1,
                        "savingsOpportunity": {
                            "savingsOpportunityPercentage": 24.60106382978723,
                            "estimatedMonthlySavings": {
                                "currency": "USD",
                                "value": 43.10091280160715,
                            },
                        },
                        "migrationEffort": "VeryLow",
                    }
                ],
            }
            for i in range(3, 6)
        ],
        "errors": [],
        "nextToken": None,
    }


@pytest.fixture()
def mocked_get_connection_status_response():
    return {"Target": "i-01234567890abcdef", "Status": "connected"}


@pytest.fixture()
def mock_get_connection_status_request(mocked_get_connection_status_response):
    return unittest.mock.MagicMock(return_value=mocked_get_connection_status_response)


@pytest.fixture(autouse=True)
def mock_get_workbench_recommendation_error_response():
    return {"instanceRecommendations": [], "errors": ["Test error"]}


@pytest.fixture()
def mock_get_ec2_instance_recommendations_error_request(
    mock_get_workbench_recommendation_error_response,
):
    return unittest.mock.MagicMock(return_value=mock_get_workbench_recommendation_error_response)


@pytest.fixture()
def mock_get_ec2_instance_recommendations_request(
    mock_get_workbench_recommendation_response,
    mock_next_get_workbench_recommendation_response,
):
    return unittest.mock.MagicMock(
        side_effect=(
            mock_get_workbench_recommendation_response,
            mock_next_get_workbench_recommendation_response,
        )
    )


@pytest.fixture()
def mock_start_ec2_instance_request():
    error_message = {
        "Error": {
            "Code": "InsufficientInstanceCapacity",
            "Message": "Insufficient instance capacity",
        }
    }
    return unittest.mock.MagicMock(
        side_effect=(ClientError(error_response=error_message, operation_name="StartInstances"))
    )


@pytest.fixture(autouse=True)
def mock_ec2_client():
    with moto.mock_aws():
        yield boto3.client(
            "ec2",
            region_name=TEST_REGION,
        )


@pytest.fixture(autouse=True)
def mock_ecs_client():
    with moto.mock_aws():
        client: ecs_client.ECSClient = boto3.client(
            "ecs",
            region_name=TEST_REGION,
        )

        # Create a cluster
        cluster_name = "test-cluster"
        client.create_cluster(clusterName=cluster_name)

        # Register a task definition
        task_definition = client.register_task_definition(
            family="test-task",
            containerDefinitions=[
                {
                    "name": "test-container",
                    "image": "nginx",
                    "memory": 512,
                    "cpu": 256,
                }
            ],
        )

        # Create a service
        service_name = "test-service"
        client.create_service(
            cluster=cluster_name,
            serviceName=service_name,
            taskDefinition=task_definition["taskDefinition"]["family"],
            desiredCount=1,
            launchType="EC2",
        )

        # Run a task under the service
        client.run_task(
            cluster=cluster_name,
            taskDefinition=task_definition["taskDefinition"]["taskDefinitionArn"],
            count=1,
            startedBy=service_name,
            launchType="FARGATE",
        )

        return client


@pytest.fixture(autouse=True)
def mock_ssm_client():
    with moto.mock_aws():
        yield boto3.client(
            "ssm",
            region_name=TEST_REGION,
        )


@pytest.fixture(autouse=True)
def mock_secretsmanager_client():
    with moto.mock_aws():
        yield boto3.client(
            "secretsmanager",
            region_name=TEST_REGION,
        )


@pytest.fixture(autouse=True)
def mock_ec2_instance(mock_ec2_client):
    response = mock_ec2_client.run_instances(ImageId="ami-12c6146b", MinCount=1, MaxCount=1)
    mock_instance_id = response["Instances"][0]["InstanceId"]
    tags = [
        {"Key": "Name", "Value": "instanceName"},
        {"Key": "Environment", "Value": "DEV"},
    ]
    mock_ec2_client.create_tags(Resources=[mock_instance_id], Tags=tags)

    return response["Instances"][0]


@pytest.fixture(autouse=True)
def mock_security_group(mock_ec2_client):
    user_id = "T0011AA"
    vpc_id = mock_ec2_client.create_vpc(CidrBlock="10.0.0.0/16").get("Vpc").get("VpcId")

    return mock_ec2_client.create_security_group(
        Description="User based security group for workbenches and virtual targets",
        GroupName=f"user-sg-123456789012-{user_id}",
        VpcId=vpc_id,
        TagSpecifications=[
            {
                "ResourceType": "security-group",
                "Tags": [
                    {
                        "Key": "vew:securityGroup:ownerId",
                        "Value": user_id,
                    },
                ],
            },
        ],
    ).get("GroupId")


@pytest.fixture(autouse=True)
def mock_stopped_ec2_instance(mock_ec2_client):
    response = mock_ec2_client.run_instances(ImageId="ami-12c6146b", MinCount=1, MaxCount=1)
    mock_instance_id = response["Instances"][0]["InstanceId"]
    mock_ec2_client.stop_instances(InstanceIds=[mock_instance_id])
    response = mock_ec2_client.describe_instances(InstanceIds=[mock_instance_id])

    return response["Reservations"][0]["Instances"][0]


@pytest.fixture
def mock_vpc(mock_ec2_client):
    return mock_ec2_client.create_vpc(
        CidrBlock="10.0.0.0/16",
        TagSpecifications=[{"ResourceType": "vpc", "Tags": [{"Key": "onboarding", "Value": "enabled"}]}],
    )


@pytest.fixture
def mock_subnets(mock_ec2_client, mock_vpc):
    subnets = []
    for i in range(3):
        resp = mock_ec2_client.create_subnet(VpcId=mock_vpc.get("Vpc").get("VpcId"), CidrBlock=f"10.0.{i}.0/24")

        subnets.append(resp)

    return subnets


@pytest.fixture
def mock_network_interface(mock_subnets, mock_ec2_client):
    return mock_ec2_client.create_network_interface(SubnetId=mock_subnets[0].get("Subnet").get("SubnetId"))


@pytest.fixture
def mock_tgw(mock_ec2_client, mock_vpc, mock_subnets):
    tgw = mock_ec2_client.create_transit_gateway()
    route_table = mock_ec2_client.create_route_table(VpcId=mock_vpc.get("Vpc").get("VpcId"))
    mock_ec2_client.create_route(
        DestinationCidrBlock="10.0.0.0/8",
        TransitGatewayId=tgw.get("TransitGateway").get("TransitGatewayId"),
        RouteTableId=route_table.get("RouteTable").get("RouteTableId"),
    )
    for s in mock_subnets:
        mock_ec2_client.associate_route_table(
            RouteTableId=route_table.get("RouteTable").get("RouteTableId"),
            SubnetId=s.get("Subnet").get("SubnetId"),
        )


@pytest.fixture
def mock_subnets_wo_tgw(mock_ec2_client, mock_vpc):
    subnets = []
    for i in range(3):
        resp = mock_ec2_client.create_subnet(VpcId=mock_vpc.get("Vpc").get("VpcId"), CidrBlock=f"10.0.{i + 3}.0/24")
        subnets.append(resp)

    return subnets


@pytest.fixture
def mock_subnet_setup(mock_tgw, mock_subnets_wo_tgw):
    pass


@pytest.fixture()
def get_sample_version():
    def _get_sample_version(
        project_id="proj-12345",
        product_id="prod-1",
        version_id="vers-1",
        aws_account_id="001234567890",
        parameters: list[version.VersionParameter] = [version.VersionParameter(parameterKey="test")],
    ):
        return version.Version(
            projectId=project_id,
            productId=product_id,
            technologyId="tech-123",
            versionId=version_id,
            versionName="v1.0.0",
            versionDescription="Descr",
            awsAccountId=aws_account_id,
            accountId="acct-guid",
            stage=version.VersionStage.DEV,
            region="us-east-1",
            amiId="ami-123",
            scProductId="prod-123",
            scProvisioningArtifactId="pa-123",
            isRecommendedVersion=True,
            parameters=parameters,
            componentVersionDetails=TEST_COMPONENT_VERSION_DETAILS,
            osVersion=TEST_OS_VERSION,
            lastUpdateDate="2023-12-06",
        )

    return _get_sample_version


@pytest.fixture()
def get_sample_provisioned_product():
    def _inner(
        project_id: str = "proj-123",
        provisioned_product_id: str = "pp-123",
        status: product_status.ProductStatus = product_status.ProductStatus.Provisioning,
        sc_provisioned_product_id: str | None = None,
        user_id: str = "T0011AA",
        stage: provisioned_product.ProvisionedProductStage = provisioned_product.ProvisionedProductStage.DEV,
        product_id: str = "prod-123",
        provisioned_product_type: provisioned_product.ProvisionedProductType = provisioned_product.ProvisionedProductType.VirtualTarget,
        experimental: bool = False,
        region: str = "us-east-1",
        product_name: str = "Pied Piper",
        version_name: str = "v1.0.0",
        version_id: str = "vers-123",
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
            productName=product_name,
            productDescription="Compression",
            technologyId="tech-123",
            versionId=version_id,
            versionName=version_name,
            awsAccountId="001234567890",
            accountId="acc-123",
            stage=stage,
            region=region,
            amiId="ami-123",
            scProductId="sc-prod-123",
            scProvisioningArtifactId="sc-pa-123",
            scProvisionedProductId=sc_provisioned_product_id,
            provisioningParameters=[
                provisioning_parameter.ProvisioningParameter(key="SomeParam", value="some-test-param-value")
            ],
            experimental=experimental,
            createDate="2023-12-05T00:00:00+00:00",
            lastUpdateDate="2023-12-05T00:00:00+00:00",
            createdBy="T0011AA",
            lastUpdatedBy="T0011AA",
        )

    return _inner
