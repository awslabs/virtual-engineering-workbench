import logging
from datetime import datetime
from unittest import mock

import boto3
import botocore
import moto
import pytest

TEST_REGION = "us-east-1"

orig = botocore.client.BaseClient._make_api_call

fake_bucket = {"Bucket": "fake_bucket", "CreateBucketConfiguration": {"LocationConstraint": "eu-west-1"}}


@pytest.fixture(autouse=True)
def s3_client_mock():
    with moto.mock_aws():
        yield boto3.client("s3", region_name=TEST_REGION)


@pytest.fixture(autouse=True)
def mock_template_file(s3_client_mock):
    s3_client_mock.create_bucket(**fake_bucket)


@pytest.fixture(autouse=True)
def mock_sts():
    with moto.mock_aws():
        yield boto3.client("sts", region_name=TEST_REGION)


@pytest.fixture()
def mock_ec2():
    with moto.mock_aws():
        yield boto3.client("ec2")


@pytest.fixture()
def mock_ecr():
    with moto.mock_aws():
        yield boto3.client("ecr")


@pytest.fixture()
def mock_logger():
    logger_mock = mock.create_autospec(spec=logging.Logger)
    return logger_mock


@pytest.fixture()
def mock_moto_calls(
    mocked_describe_portfolio_response,
    mocked_create_portfolio_response,
    mocked_create_portfolio_share_response,
    mocked_accept_portfolio_share_response,
    mocked_associate_principal_with_portfolio_response,
    mocked_create_provisioning_artifact_response,
    mocked_create_product_response,
    mocked_associate_product_with_portfolio_response,
    mocked_create_constraint_response,
    mocked_describe_product_as_admin_response,
    mocked_describe_provisioning_artifact_response,
    mocked_delete_provisioning_artifact_response,
    mocked_list_constraints_for_portfolio_response,
    mocked_modify_image_attribute_response,
    mocked_update_provisioning_artifact_response,
    mocked_disassociate_product_from_portfolio_response,
    mocked_delete_product_response,
    mocked_describe_images_response,
    mocked_disassociate_principal_from_portfolio_response,
    mocked_list_principals_for_portfolio_response,
    mocked_validate_template_response,
    mocked_list_launch_paths_response,
    mocked_describe_provisioning_parameters_response,
):
    describe_portfolio_name = "DescribePortfolio"
    create_portfolio_name = "CreatePortfolio"
    create_portfolio_share_name = "CreatePortfolioShare"
    accept_portfolio_share_name = "AcceptPortfolioShare"
    associate_principal_with_portfolio_name = "AssociatePrincipalWithPortfolio"
    disassociate_principal_from_portfolio_name = "DisassociatePrincipalFromPortfolio"
    list_principals_for_portfolio_name = "ListPrincipalsForPortfolio"
    create_provisioning_artifact_name = "CreateProvisioningArtifact"
    create_product_name = "CreateProduct"
    associate_product_with_portfolio_name = "AssociateProductWithPortfolio"
    create_constraint_name = "CreateConstraint"
    describe_product_as_admin_name = "DescribeProductAsAdmin"
    describe_provisioning_artifact_name = "DescribeProvisioningArtifact"
    delete_provisioning_artifact_name = "DeleteProvisioningArtifact"
    list_constraints_for_portfolio_name = "ListConstraintsForPortfolio"
    mocked_modify_image_attribute_name = "ModifyImageAttribute"
    mocked_update_provisioning_artifact_name = "UpdateProvisioningArtifact"
    mocked_disassociate_product_from_portfolio_name = "DisassociateProductFromPortfolio"
    mocked_delete_product_name = "DeleteProduct"
    mocked_describe_images_name = "DescribeImages"
    mocked_validate_template_name = "ValidateTemplate"
    mocked_list_launch_paths_name = "ListLaunchPaths"
    mocked_describe_provisioning_parameters_name = "DescribeProvisioningParameters"
    mocked_create_grant_name = "CreateGrant"

    invocations = {
        describe_portfolio_name: mock.MagicMock(return_value=mocked_describe_portfolio_response),
        create_portfolio_name: mock.MagicMock(return_value=mocked_create_portfolio_response),
        create_portfolio_share_name: mock.MagicMock(return_value=mocked_create_portfolio_share_response),
        accept_portfolio_share_name: mock.MagicMock(return_value=mocked_accept_portfolio_share_response),
        associate_principal_with_portfolio_name: mock.MagicMock(
            return_value=mocked_associate_principal_with_portfolio_response
        ),
        disassociate_principal_from_portfolio_name: mock.MagicMock(
            return_value=mocked_disassociate_principal_from_portfolio_response
        ),
        list_principals_for_portfolio_name: mock.MagicMock(return_value=mocked_list_principals_for_portfolio_response),
        create_provisioning_artifact_name: mock.MagicMock(return_value=mocked_create_provisioning_artifact_response),
        create_product_name: mock.MagicMock(return_value=mocked_create_product_response),
        associate_product_with_portfolio_name: mock.MagicMock(
            return_value=mocked_associate_product_with_portfolio_response
        ),
        create_constraint_name: mock.MagicMock(return_value=mocked_create_constraint_response),
        describe_product_as_admin_name: mock.MagicMock(return_value=mocked_describe_product_as_admin_response),
        describe_provisioning_artifact_name: mock.MagicMock(
            return_value=mocked_describe_provisioning_artifact_response
        ),
        delete_provisioning_artifact_name: mock.MagicMock(return_value=mocked_delete_provisioning_artifact_response),
        list_constraints_for_portfolio_name: mock.MagicMock(
            return_value=mocked_list_constraints_for_portfolio_response
        ),
        mocked_modify_image_attribute_name: mock.MagicMock(return_value=mocked_modify_image_attribute_response),
        mocked_update_provisioning_artifact_name: mock.MagicMock(
            return_value=mocked_update_provisioning_artifact_response
        ),
        mocked_disassociate_product_from_portfolio_name: mock.MagicMock(
            return_value=mocked_disassociate_product_from_portfolio_response
        ),
        mocked_delete_product_name: mock.MagicMock(return_value=mocked_delete_product_response),
        mocked_describe_images_name: mock.MagicMock(return_value=mocked_describe_images_response),
        mocked_validate_template_name: mock.MagicMock(return_value=mocked_validate_template_response),
        mocked_list_launch_paths_name: mock.MagicMock(return_value=mocked_list_launch_paths_response),
        mocked_describe_provisioning_parameters_name: mock.MagicMock(
            return_value=mocked_describe_provisioning_parameters_response
        ),
        mocked_create_grant_name: mock.MagicMock(
            return_value={"GrantToken": "fake-grant-token", "GrantId": "fake-grant-id"}
        ),
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture
def mocked_describe_portfolio_response():
    return {
        "PortfolioDetail": {
            "Id": "string",
            "ARN": "string",
            "DisplayName": "string",
            "Description": "string",
            "CreatedTime": datetime(2015, 1, 1),
            "ProviderName": "string",
        },
        "Tags": [
            {"Key": "string", "Value": "string"},
        ],
        "TagOptions": [
            {"Key": "string", "Value": "string", "Active": True, "Id": "string", "Owner": "string"},
        ],
        "Budgets": [
            {"BudgetName": "string"},
        ],
    }


@pytest.fixture
def mocked_create_portfolio_response():
    return {
        "PortfolioDetail": {
            "ARN": "string",
            "CreatedTime": 123456789,
            "Description": "string",
            "DisplayName": "string",
            "Id": "sc-port-00000",
            "ProviderName": "string",
        },
        "Tags": [{"Key": "string", "Value": "string"}],
    }


@pytest.fixture
def mocked_create_portfolio_share_response():
    return {"PortfolioShareToken": "string"}


@pytest.fixture
def mocked_accept_portfolio_share_response():
    return None


@pytest.fixture
def mocked_associate_principal_with_portfolio_response():
    return None


@pytest.fixture
def mocked_disassociate_principal_from_portfolio_response():
    return None


@pytest.fixture
def mocked_list_principals_for_portfolio_response():
    return {
        "NextPageToken": None,
        "Principals": [{"PrincipalARN": "arn:aws:iam::123456789013:role/my-role", "PrincipalType": "IAM"}],
    }


@pytest.fixture
def mocked_create_provisioning_artifact_response():
    return {
        "ProvisioningArtifactDetail": {
            "Id": "pa-12345",
            "Name": "string",
            "Description": "string",
            "Type": "CLOUD_FORMATION_TEMPLATE",
            "CreatedTime": datetime(2023, 7, 17),
            "Active": True,
            "Guidance": "DEFAULT",
            "SourceRevision": "string",
        },
        "Info": {"string": "string"},
        "Status": "CREATING",
    }


@pytest.fixture
def mocked_create_product_response():
    return {
        "ProductViewDetail": {
            "ProductViewSummary": {
                "Id": "string",
                "ProductId": "prod-12345",
                "Name": "string",
                "Owner": "string",
                "ShortDescription": "string",
                "Type": "CLOUD_FORMATION_TEMPLATE",
                "Distributor": "string",
                "HasDefaultPath": True,
                "SupportEmail": "string",
                "SupportDescription": "string",
                "SupportUrl": "string",
            },
            "Status": "CREATING",
            "ProductARN": "string",
            "CreatedTime": datetime(2023, 7, 17),
            "SourceConnection": {
                "Type": "CODESTAR",
                "ConnectionParameters": {
                    "CodeStar": {
                        "ConnectionArn": "string",
                        "Repository": "string",
                        "Branch": "string",
                        "ArtifactPath": "string",
                    }
                },
                "LastSync": {
                    "LastSyncTime": datetime(2023, 7, 17),
                    "LastSyncStatus": "SUCCEEDED",
                    "LastSyncStatusMessage": "string",
                    "LastSuccessfulSyncTime": datetime(2023, 7, 17),
                    "LastSuccessfulSyncProvisioningArtifactId": "string",
                },
            },
        },
        "ProvisioningArtifactDetail": {
            "Id": "pa-12345",
            "Name": "string",
            "Description": "string",
            "Type": "CLOUD_FORMATION_TEMPLATE",
            "CreatedTime": datetime(2023, 7, 17),
            "Active": True,
            "Guidance": "DEFAULT",
            "SourceRevision": "string",
        },
        "Tags": [
            {"Key": "string", "Value": "string"},
        ],
    }


@pytest.fixture
def mocked_associate_product_with_portfolio_response():
    return None


@pytest.fixture
def mocked_create_constraint_response():
    return {
        "ConstraintDetail": {
            "ConstraintId": "string",
            "Type": "string",
            "Description": "string",
            "Owner": "string",
            "ProductId": "string",
            "PortfolioId": "string",
        },
        "ConstraintParameters": "string",
        "Status": "AVAILABLE",
    }


@pytest.fixture
def mocked_describe_product_as_admin_response():
    return {
        "ProductViewDetail": {
            "ProductViewSummary": {
                "Id": "string",
                "ProductId": "prod-12345",
                "Name": "string",
                "Owner": "string",
                "ShortDescription": "string",
                "Type": "CLOUD_FORMATION_TEMPLATE",
                "Distributor": "string",
                "HasDefaultPath": True,
                "SupportEmail": "string",
                "SupportDescription": "string",
                "SupportUrl": "string",
            },
            "Status": "AVAILABLE",
            "ProductARN": "string",
            "CreatedTime": datetime(2023, 7, 17),
            "SourceConnection": {
                "Type": "CODESTAR",
                "ConnectionParameters": {
                    "CodeStar": {
                        "ConnectionArn": "string",
                        "Repository": "string",
                        "Branch": "string",
                        "ArtifactPath": "string",
                    }
                },
                "LastSync": {
                    "LastSyncTime": datetime(2023, 7, 17),
                    "LastSyncStatus": "SUCCEEDED",
                    "LastSyncStatusMessage": "string",
                    "LastSuccessfulSyncTime": datetime(2023, 7, 17),
                    "LastSuccessfulSyncProvisioningArtifactId": "string",
                },
            },
        },
        "ProvisioningArtifactSummaries": [
            {
                "Id": "string",
                "Name": "string",
                "Description": "string",
                "CreatedTime": datetime(2015, 1, 1),
                "ProvisioningArtifactMetadata": {"string": "string"},
            },
        ],
        "Tags": [
            {"Key": "string", "Value": "string"},
        ],
        "TagOptions": [
            {"Key": "string", "Value": "string", "Active": True, "Id": "string", "Owner": "string"},
        ],
        "Budgets": [
            {"BudgetName": "string"},
        ],
    }


@pytest.fixture
def mocked_describe_provisioning_artifact_response():
    return {
        "ProvisioningArtifactDetail": {
            "Id": "pa-12345",
            "Name": "string",
            "Description": "string",
            "Type": "CLOUD_FORMATION_TEMPLATE",
            "CreatedTime": datetime(2023, 7, 17),
            "Active": True,
            "Guidance": "DEFAULT",
            "SourceRevision": "string",
        },
        "Info": {"string": "string"},
        "Status": "AVAILABLE",
        "ProvisioningArtifactParameters": [
            {
                "ParameterKey": "key-1",
                "DefaultValue": "value-1",
                "ParameterType": "string",
                "IsNoEcho": True,
                "Description": "description-1",
                "ParameterConstraints": {
                    "AllowedValues": ["value-1", "value-2", "value-3"],
                    "AllowedPattern": "[A-Za-z0-9]+",
                    "ConstraintDescription": "description",
                    "MaxLength": "10",
                    "MinLength": "1",
                    "MaxValue": "1000",
                    "MinValue": "0",
                },
            },
            {
                "ParameterKey": "key-2",
            },
        ],
    }


@pytest.fixture
def mocked_delete_provisioning_artifact_response():
    return None


@pytest.fixture
def mocked_list_constraints_for_portfolio_response():
    return {
        "ConstraintDetails": [
            {
                "ConstraintId": "cons-12345",
                "Type": "LAUNCH",
                "Description": "string",
                "Owner": "string",
                "ProductId": "string",
                "PortfolioId": "string",
            },
            {
                "ConstraintId": "cons-00000",
                "Type": "NOTIFICATION",
                "Description": "string",
                "Owner": "string",
                "ProductId": "string",
                "PortfolioId": "string",
            },
            {
                "ConstraintId": "cons-56789",
                "Type": "RESOURCE_UPDATE",
                "Description": "string",
                "Owner": "string",
                "ProductId": "string",
                "PortfolioId": "string",
            },
        ],
        "NextPageToken": "string",
    }


@pytest.fixture
def mocked_modify_image_attribute_response():
    return {
        "ResponseMetadata": {
            "...": "...",
        },
    }


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """Mocked AWS Credentials for moto."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture()
def mocked_update_provisioning_artifact_response():
    return {
        "ProvisioningArtifactDetail": {
            "Id": "string",
            "Name": "string",
            "Description": "string",
            "Type": "CLOUD_FORMATION_TEMPLATE",
            "CreatedTime": datetime(2015, 1, 1),
            "Active": False,
            "Guidance": "DEFAULT",
            "SourceRevision": "string",
        },
        "Info": {"string": "string"},
        "Status": "CREATING",
    }


@pytest.fixture()
def mocked_describe_images_response():
    return {
        "Images": [
            {
                "Architecture": "x86_64",
                "CreationDate": "2023-08-28T00:00:00+00:00",
                "ImageId": "ami-12345",
                "ImageLocation": "string",
                "ImageType": "machine",
                "Public": True,
                "KernelId": "string",
                "OwnerId": "string",
                "Platform": "Windows",
                "PlatformDetails": "string",
                "UsageOperation": "string",
                "ProductCodes": [
                    {"ProductCodeId": "string", "ProductCodeType": "devpay"},
                ],
                "RamdiskId": "string",
                "State": "available",
                "BlockDeviceMappings": [
                    {
                        "DeviceName": "string",
                        "VirtualName": "string",
                        "Ebs": {
                            "DeleteOnTermination": True,
                            "Iops": 123,
                            "SnapshotId": "string",
                            "VolumeSize": 123,
                            "VolumeType": "standard",
                            "KmsKeyId": "string",
                            "Throughput": 123,
                            "OutpostArn": "string",
                            "Encrypted": True,
                        },
                        "NoDevice": "string",
                    },
                ],
                "Description": "Test image description",
                "EnaSupport": True,
                "Hypervisor": "ovm",
                "ImageOwnerAlias": "string",
                "Name": "Test image name",
                "RootDeviceName": "string",
                "RootDeviceType": "ebs",
                "SriovNetSupport": "string",
                "StateReason": {"Code": "string", "Message": "string"},
                "Tags": [
                    {"Key": "string", "Value": "string"},
                ],
                "VirtualizationType": "hvm",
                "BootMode": "uefi-preferred",
                "TpmSupport": "v2.0",
                "DeprecationTime": "string",
                "ImdsSupport": "v2.0",
            },
        ],
        "NextToken": None,
    }


@pytest.fixture()
def mocked_disassociate_product_from_portfolio_response():
    return {}


@pytest.fixture()
def mocked_delete_product_response():
    return {}


@pytest.fixture()
def mocked_validate_template_response():
    return {
        "Parameters": [
            {
                "ParameterKey": "parameter-1",
                "DefaultValue": "value-1",
                "NoEcho": True,
                "Description": "description",
            },
            {
                "ParameterKey": "parameter-2",
            },
        ],
        "Description": "string",
        "Capabilities": [
            "CAPABILITY_IAM",
        ],
        "CapabilitiesReason": "string",
        "DeclaredTransforms": [
            "string",
        ],
    }


@pytest.fixture()
def mocked_list_launch_paths_response():
    return {
        "LaunchPathSummaries": [
            {
                "Id": "lpv3-s7gzphgv4eabi",
                "ConstraintSummaries": [{"Type": "LAUNCH"}, {"Type": "NOTIFICATION"}],
                "Tags": [],
                "Name": "portfolio-tech-tvrjp-00000000000",
            }
        ],
        "ResponseMetadata": {
            "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "content-type": "application/x-amz-json-1.1",
                "content-length": "172",
                "date": "Fri, 24 Nov 2023 16:31:36 GMT",
            },
            "RetryAttempts": 0,
        },
    }


@pytest.fixture()
def mocked_describe_provisioning_parameters_response():
    return {
        "ProvisioningArtifactParameters": [
            {
                "ParameterKey": "SubnetIdSSM",
                "DefaultValue": "/workbench/vpc/privatesubnet-id-balanced",
                "ParameterType": "AWS::SSM::Parameter::Value<String>",
                "IsNoEcho": False,
                "ParameterConstraints": {"AllowedValues": []},
            },
            {
                "ParameterKey": "VpcIdSSM",
                "DefaultValue": "/workbench/vpc/vpc-id",
                "ParameterType": "AWS::SSM::Parameter::Value<String>",
                "IsNoEcho": False,
                "ParameterConstraints": {"AllowedValues": []},
            },
            {
                "ParameterKey": "InstanceType",
                "DefaultValue": "c8i.8xlarge",
                "ParameterType": "String",
                "IsNoEcho": False,
                "Description": "Amazon EC2 Instance Type",
                "ParameterConstraints": {"AllowedValues": ["c8i.8xlarge", "c8i.12xlarge", "c8i.16xlarge"]},
            },
            {
                "ParameterKey": "VolumeSize",
                "DefaultValue": "250",
                "ParameterType": "String",
                "IsNoEcho": False,
                "Description": "Amazon EBS Volume Size",
                "ParameterConstraints": {"AllowedValues": ["250", "350", "500"]},
            },
            {
                "ParameterKey": "OwnerTID",
                "DefaultValue": "",
                "ParameterType": "String",
                "IsNoEcho": False,
                "Description": "Owner TID",
            },
            {
                "ParameterKey": "SubnetId",
                "DefaultValue": "",
                "ParameterType": "AWS::EC2::Subnet::Id",
                "IsNoEcho": False,
                "Description": "Subnet ID where workbench is provisioned. VEW provides a subnet with the most IPs remaining.",
            },
            {
                "ParameterKey": "SubnetsIds",
                "DefaultValue": "",
                "ParameterType": "List<AWS::EC2::Subnet::Id>",
                "IsNoEcho": False,
                "Description": "Subnet ID where container is provisioned",
            },
        ],
        "ConstraintSummaries": [{"Type": "LAUNCH"}, {"Type": "NOTIFICATION"}],
        "UsageInstructions": [
            {"Type": "rules", "Value": "{}"},
            {"Type": "version", "Value": "2010-09-09"},
            {"Type": "capabilitiesReason", "Value": "The following resource(s) require capabilities: [AWS::IAM::Role]"},
            {"Type": "description", "Value": "Version 1.1.1-rc.1 template for Some Workbench"},
            {
                "Type": "metadata",
                "Value": '{"ProductVersionMetaData":{"InstalledTools":{"Label":"Installed Tools","Value":"https://example.com"},"ReleaseNotes":{"Label":"Release Notes","Value":"https://example.com"},"MainSoftware":{"Label":"Main Software Versions","Value":["Main SOftware"]}},"AWS::CloudFormation::Interface":{"ParameterLabels":{"InstanceType":{"default":"What type of workbench do you want to start?"},"VolumeSize":{"default":"How much storage would you like to have?"}}},"ParameterAllowedValueLabels":{"InstanceType":{"c8i.12xlarge":"Compute Optimized M - 48 vCPU, 96 GiB RAM","c8i.8xlarge":"Compute Optimized S - 32 vCPU, 64 GiB RAM","c8i.16xlarge":"Compute Optimized L - 64 vCPU, 128 GiB RAM"},"VolumeSize":{"250":"Disk S - 250 GB Storage","500":"Disk L - 500 GB Storage","350":"Disk M - 350 GB Storage"}}, "ParameterMetadata":{"VolumeSize":{"OptionWarnings":{"250":"Very expensive"}}}}',
            },
            {"Type": "launchAsRole", "Value": "arn:aws:iam::00000000000:role/ProductPublishingLaunchConstraintRole"},
            {"Type": "tagUpdateOnProvisionedProduct", "Value": "NOT_ALLOWED"},
            {"Type": "capability", "Value": "CAPABILITY_IAM"},
        ],
        "TagOptions": [],
        "ProvisioningArtifactPreferences": {},
        "ProvisioningArtifactOutputs": [
            {"Key": "pa-00000000", "Description": "Initial live version"},
            {"Key": "pa-1111111111", "Description": "Fixed metadata"},
        ],
        "ProvisioningArtifactOutputKeys": [
            {"Key": "FeatureToggles", "Description": "Enabled features for this workbench"},
            {"Key": "InstanceId", "Description": "InstanceId of the newly created EC2 instance"},
            {"Key": "PrivateIP", "Description": "Private IP address of the newly created EC2 instance"},
        ],
        "ResponseMetadata": {
            "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "HTTPStatusCode": 200,
            "HTTPHeaders": {
                "x-amzn-requestid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                "content-type": "application/x-amz-json-1.1",
                "content-length": "3673",
                "date": "Fri, 24 Nov 2023 16:11:47 GMT",
            },
            "RetryAttempts": 0,
        },
    }
