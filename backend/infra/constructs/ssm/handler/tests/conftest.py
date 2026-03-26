import os
import unittest

import boto3
import botocore
import moto
import pytest
from attr import dataclass

orig = botocore.client.BaseClient._make_api_call


@pytest.fixture
def lambda_context():
    @dataclass
    class context:
        function_name = "test"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:eu-west-1:000000000:function:test"
        aws_request_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    return context


@pytest.fixture()
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(autouse=True)
def mock_ram(aws_credentials):
    with moto.mock_aws():
        yield boto3.client("ram", region_name="us-east-1")


@pytest.fixture
def payload():
    def __inner(resource_type: str):
        return {
            "RequestType": resource_type,
            "ServiceToken": "arn:aws:lambda:us-west-2:123456789012:function:my-custom-resource",
            "ResponseURL": "http://pre-signed-S3-url-for-response",
            "StackId": "arn:aws:cloudformation:us-west-2:123456789012:stack/my-stack-name/abc123-def456",
            "RequestId": "unique-request-id-for-this-operation",
            "LogicalResourceId": "MyCustomResource",
            "ResourceType": "Custom::MyResourceType",
            "ResourceProperties": {"Name": "resource-share-name"},
        }

    return __inner


@pytest.fixture(autouse=True)
def mock_moto_error_calls(
    mocked_get_resource_share_invitations_request, mocked_accept_resource_share_invitation_request
):
    invocations = {
        "GetResourceShareInvitations": mocked_get_resource_share_invitations_request,
        "AcceptResourceShareInvitation": mocked_accept_resource_share_invitation_request,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with unittest.mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture()
def mocked_get_resource_share_invitations_response():
    return {
        "resourceShareInvitations": [
            {
                "resourceShareInvitationArn": "invitation-arn",
                "resourceShareName": "resource-share-name",
                "resourceShareArn": "share-arn",
                "senderAccountId": "string",
                "receiverAccountId": "string",
                "invitationTimestamp": "2025-01-16",
                "status": "PENDING",
                "resourceShareAssociations": [
                    {
                        "resourceShareArn": "string",
                        "resourceShareName": "string",
                        "associatedEntity": "string",
                        "associationType": "PRINCIPAL",
                        "status": "ASSOCIATED",
                        "statusMessage": "string",
                        "creationTime": "2025-01-16",
                        "lastUpdatedTime": "2025-01-16",
                        "external": False,
                    },
                ],
                "receiverArn": "string",
            },
        ],
    }


@pytest.fixture()
def mocked_get_resource_share_invitations_request(mocked_get_resource_share_invitations_response):
    return unittest.mock.MagicMock(return_value=mocked_get_resource_share_invitations_response)


@pytest.fixture()
def mocked_accept_resource_share_invitation_response():
    return {
        "resourceShareInvitation": {
            "resourceShareInvitationArn": "invitation-arn",
            "resourceShareName": "resource-share-name",
            "resourceShareArn": "share-arn",
            "senderAccountId": "string",
            "receiverAccountId": "string",
            "invitationTimestamp": "2025-01-16",
            "status": "PENDING",
            "resourceShareAssociations": [
                {
                    "resourceShareArn": "string",
                    "resourceShareName": "string",
                    "associatedEntity": "string",
                    "associationType": "PRINCIPAL",
                    "status": "ASSOCIATED",
                    "statusMessage": "string",
                    "creationTime": "2025-01-16",
                    "lastUpdatedTime": "2025-01-16",
                    "external": False,
                },
            ],
            "receiverArn": "string",
        },
    }


@pytest.fixture()
def mocked_accept_resource_share_invitation_request(mocked_accept_resource_share_invitation_response):
    return unittest.mock.MagicMock(return_value=mocked_accept_resource_share_invitation_response)
