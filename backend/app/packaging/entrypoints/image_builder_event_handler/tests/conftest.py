import json
import tempfile
from enum import Enum
from unittest import mock

import boto3
import botocore
import moto
import pytest
from attr import dataclass

from app.packaging.domain.ports import image_query_service, pipeline_query_service
from app.packaging.entrypoints.image_builder_event_handler.model import image_builder_image_status


class GlobalVariables(Enum):
    TEST_TABLE_NAME = "TEST"
    TEST_REGION = "us-east-1"
    TEST_AMI_ID = "ami-01a23bc4def5a6789"
    TEST_BUILD_IMAGE_ARN = "arn:aws:imagebuilder:us-west-1:123456789012:image/proserve-test-image/1.0.0/3"
    TEST_PIPELINE_ID = "proserve-test-image-pipeline"
    TEST_PIPELINE_ARN = f"arn:aws:imagebuilder:us-west-1:123456789012:image-pipeline/{TEST_PIPELINE_ID}"


orig = botocore.client.BaseClient._make_api_call


@pytest.fixture(autouse=True)
def mock_sts():
    with moto.mock_aws():
        yield boto3.client("sts", region_name=GlobalVariables.TEST_REGION.value)


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
    monkeypatch.setenv("TABLE_NAME", GlobalVariables.TEST_TABLE_NAME.value)


@pytest.fixture
def generate_event():
    def _generate_event(image_status: str):
        message = json.dumps(
            {
                "versionlessArn": "arn:aws:imagebuilder:us-west-1:123456789012:image/proserve-test-image",
                "semver": 1237940039285380274899124227,
                "arn": GlobalVariables.TEST_BUILD_IMAGE_ARN.value,
                "name": "proserve-test-image",
                "version": "1.0.0",
                "type": "AMI",
                "buildVersion": 3,
                "state": {"status": image_status},
                "platform": "Linux",
                "imageRecipe": {
                    "arn": "arn:aws:imagebuilder:us-west-1:123456789012:image-recipe/proserve-test-image/1.0.0",
                    "name": "proserve-test-image",
                    "version": "1.0.0",
                    "components": [
                        {"componentArn": "arn:aws:imagebuilder:us-west-1:123456789012:component/update-linux/1.0.2/1"}
                    ],
                    "platform": "Linux",
                    "parentImage": "arn:aws:imagebuilder:us-west-1:987654321098:image/amazon-linux-2-x86/2022.6.14/1",
                    "blockDeviceMappings": [
                        {
                            "deviceName": "/dev/xvda",
                            "ebs": {
                                "encrypted": False,
                                "deleteOnTermination": True,
                                "volumeSize": 8,
                                "volumeType": "gp2",
                            },
                        }
                    ],
                    "dateCreated": "Feb 24, 2021 12:31:54 AM",
                    "tags": {
                        "internalId": "1a234567-8901-2345-bcd6-ef7890123456",
                        "resourceArn": "arn:aws:imagebuilder:us-west-1:123456789012:image-recipe/proserve-test-image/1.0.0",
                    },
                    "workingDirectory": tempfile.gettempdir(),
                    "accountId": "462045008730",
                },
                "sourcePipelineArn": GlobalVariables.TEST_PIPELINE_ARN.value,
                "infrastructureConfiguration": {
                    "arn": "arn:aws:imagebuilder:us-west-1:123456789012:infrastructure-configuration/example-linux-infra-config-uswest1",
                    "name": "example-linux-infra-config-uswest1",
                    "instanceProfileName": "example-linux-ib-baseline-admin",
                    "tags": {
                        "internalId": "234abc56-d789-0123-a4e5-6b789d012c34",
                        "resourceArn": "arn:aws:imagebuilder:us-west-1:123456789012:infrastructure-configuration/example-linux-infra-config-uswest1",
                    },
                    "logging": {"s3Logs": {"s3BucketName": "12345-example-linux-testbucket-uswest1"}},
                    "keyPair": "example-linux-key-pair-uswest1",
                    "terminateInstanceOnFailure": True,
                    "snsTopicArn": "arn:aws:sns:us-west-1:123456789012:example-linux-ibnotices-uswest1",
                    "dateCreated": "Feb 24, 2021 12:31:55 AM",
                    "accountId": "123456789012",
                },
                "imageTestsConfigurationDocument": {"imageTestsEnabled": True, "timeoutMinutes": 720},
                "distributionConfiguration": {
                    "arn": "arn:aws:imagebuilder:us-west-1:123456789012:distribution-configuration/example-linux-distribution",
                    "name": "example-linux-distribution",
                    "dateCreated": "Feb 24, 2021 12:31:56 AM",
                    "distributions": [{"region": "us-west-1", "amiDistributionConfiguration": {}}],
                    "tags": {
                        "internalId": "345abc67-8910-12d3-4ef5-67a8b90c12de",
                        "resourceArn": "arn:aws:imagebuilder:us-west-1:123456789012:distribution-configuration/example-linux-distribution",
                    },
                    "accountId": "123456789012",
                },
                "dateCreated": "Jul 28, 2022 1:13:45 AM",
                "outputResources": {
                    "amis": (
                        [
                            {
                                "region": "us-west-1",
                                "image": GlobalVariables.TEST_AMI_ID.value,
                                "name": "example-linux-image 2022-07-28T01-14-17.416Z",
                                "accountId": "123456789012",
                            }
                        ]
                        if image_status == image_builder_image_status.ImageBuilderImageStatus.Available
                        else []
                    )
                },
                "buildExecutionId": "ab0cd12e-34fa-5678-b901-2c3456d789e0",
                "testExecutionId": "6a7b8901-cdef-234a-56b7-8cd89ef01234",
                "distributionJobId": "1f234567-8abc-9d0e-1234-fa56b7c890de",
                "integrationJobId": "432109b8-afe7-6dc5-4321-0ba98f7654e3",
                "accountId": "123456789012",
                "osVersion": "Amazon Linux 2",
                "enhancedImageMetadataEnabled": True,
                "buildType": "USER_INITIATED",
                "tags": {
                    "internalId": "901e234f-a567-89bc-0123-d4e567f89a01",
                    "resourceArn": GlobalVariables.TEST_BUILD_IMAGE_ARN.value,
                },
            }
        )

        return {
            "version": "0",
            "id": "162fc80d-b43c-09da-bae4-54471eebcf0f",
            "detail-type": "Image Builder SNS notification",
            "source": "Workbench Image Service",
            "account": "1234567890",
            "time": "2022-11-14T17:15:50Z",
            "region": "us-east-1",
            "resources": ["Image Builder"],
            "detail": {
                "Type": "Notification",
                "MessageId": "cbed64b9-6e1f-53e6-9019-3f5514199303",
                "TopicArn": "arn:aws:sns:us-east-1:1234567890:ImageBuilderPackagingSnsTopic",
                "Subject": "ImageBuilder Packaging SNS Topic",
                "Message": message,
                "Timestamp": "2022-11-14T17:15:50.354Z",
                "SignatureVersion": "1",
                "Signature": "tYFzEhwo3IiN6zhziHSPo3OmHmq9em+smADDEroPecU0ALuQO+LM6HucCfpNyeZJRd/ipVZA3XG483op7oVp8YpeQKm4KbABD6leFVRQnXxS1bRMZTgaXVGSi+jW5Nw3sZERInMQQ69RlO8K+AT5yooDJ7UiaQA/KxhkfXg/FsB9JKJhyDOPf/We4ICwuoMejy6kESQjUUNN2mLF1+oZc9yv0lrR82BEKDZGhZGHkwJuqXCWOaeD/9O2JJEWT4yRUqVp78YbXzodboJ96y43u77YFRBE1M1PqDI2efIiqWBpnO2UlGD1Kg3OFylTKEDA7bd32WjKBvXw4VhyXTEPTw==",
                "SigningCertUrl": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-56e67fcb41f6fec09b0196692625d385.pem",
                "UnsubscribeUrl": "https://sns.us-east-1.amazonaws.com/?Action=Unsubscribe&SubscriptionArn=arn:aws:sns:us-east-1:1234567890:Message2EventTransformerTopic:7f2ce100-5be2-48fc-879c-f0920eb3f1fc",
                "MessageAttributes": {},
            },
        }

    return _generate_event


@pytest.fixture(autouse=True)
def mock_image_query_srv():
    return mock.create_autospec(spec=image_query_service.ImageQueryService)


@pytest.fixture(autouse=True)
def mock_pipeline_query_srv():
    return mock.create_autospec(spec=pipeline_query_service.PipelineQueryService)
