import logging
import unittest

import boto3
import botocore
import moto
import pytest

from app.shared.adapters.boto.boto_provider import BotoProvider, BotoProviderOptions
from app.shared.adapters.boto.dict_context_provider import DictCtxProvider

orig = botocore.client.BaseClient._make_api_call


@pytest.fixture()
def logger():
    return logging.getLogger()


@pytest.fixture()
def mock_context_provider():
    return DictCtxProvider()


@pytest.fixture()
def provider(logger):
    ctx = DictCtxProvider()
    return BotoProvider(
        ctx,
        logger,
        default_options=BotoProviderOptions(
            aws_role_name="TestRole",
            aws_session_name="TestSession",
        ),
    )


@pytest.fixture()
def mock_local_ec2():
    with moto.mock_aws():
        yield boto3.client("ec2")


@pytest.fixture
def mock_ec2(aws_credentials, provider):
    with moto.mock_aws():
        yield provider.client("ec2")(BotoProviderOptions(aws_account_id="012345678900", aws_region="us-east-1"))


@pytest.fixture
def mock_ec2_client_provider(mock_ec2):
    def _inner(account_id: str, region: str):
        return mock_ec2

    return _inner


@pytest.fixture
def mock_vpc_endpoint(mock_ec2):
    vpc_id = mock_ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]

    mock_ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        ServiceName="s3",
        VpcEndpointType="Gateway",
    )

    resp = mock_ec2.create_vpc_endpoint(
        VpcId=vpc_id,
        ServiceName="com.amazonaws.us-east-1.execute-api",
        VpcEndpointType="Interface",
    )
    return resp


@pytest.fixture
def mock_vpc(mock_ec2):
    return mock_ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]


@pytest.fixture
def mock_sg(mock_ec2, mock_vpc):
    sg = mock_ec2.create_security_group(GroupName="Test", Description="Test", VpcId=mock_vpc)
    mock_ec2.create_tags(Resources=[sg.get("GroupId")], Tags=[{"Key": "Name", "Value": "Test"}])
    return mock_ec2.describe_security_groups(GroupIds=[sg.get("GroupId")])["SecurityGroups"][0]


@pytest.fixture
def mock_apigw(aws_credentials):
    with moto.mock_aws():
        yield boto3.client("apigateway")


@pytest.fixture
def mock_apigw_client_provider(mock_apigw):
    def _inner(region: str):
        return mock_apigw

    return _inner


@pytest.fixture
def mock_restapis(mock_apigw):
    apis = [
        mock_apigw.create_rest_api(
            name="test", endpointConfiguration={"types": ["PRIVATE"]}, policy='{\\"a\\": \\"b\\"}'
        ),
        mock_apigw.create_rest_api(name="test", tags={"a": "b"}),
    ]
    return apis


@pytest.fixture
def mock_restapi(mock_apigw):
    api = mock_apigw.create_rest_api(
        name="test", endpointConfiguration={"types": ["PRIVATE"]}, policy='{ \\"a\\": \\"b\\"}'
    )
    resources = mock_apigw.get_resources(restApiId=api.get("id"))
    root_id = [resource for resource in resources["items"] if resource["path"] == "/"][0]["id"]
    mock_apigw.put_method(
        restApiId=api.get("id"),
        resourceId=root_id,
        httpMethod="GET",
        authorizationType="NONE",
    )
    mock_apigw.put_method_response(restApiId=api.get("id"), resourceId=root_id, httpMethod="GET", statusCode="200")
    mock_apigw.put_integration(
        restApiId=api.get("id"),
        resourceId=root_id,
        httpMethod="GET",
        type="HTTP",
        uri="http://httpbin.org/robots.txt",
        integrationHttpMethod="POST",
    )
    mock_apigw.put_integration_response(
        restApiId=api.get("id"),
        resourceId=root_id,
        httpMethod="GET",
        statusCode="200",
        responseTemplates={},
    )
    return api


@pytest.fixture
def mock_ram(aws_credentials):
    with moto.mock_aws():
        yield boto3.client("ram")


@pytest.fixture
def mock_stepfunctions(aws_credentials):
    with moto.mock_aws():
        yield boto3.client("stepfunctions")


@pytest.fixture
def mock_ram_client_provider(mock_ram):
    def _inner(region: str):
        return mock_ram

    return _inner


@pytest.fixture
def mock_ram_share(mock_ram):
    return mock_ram.create_resource_share(name="test", tags=[{"key": "test-key", "value": "test-value"}])


@pytest.fixture(autouse=True)
def mock_associate_resource_share_response():
    return {
        "resourceShareAssociations": [
            {
                "resourceShareArn": "ram-arn",
                "resourceShareName": "ram name",
                "associatedEntity": "string",
                "associationType": "PRINCIPAL",
                "status": "ASSOCIATING",
                "statusMessage": "string",
                "creationTime": "2025-01-09",
                "lastUpdatedTime": "2025-01-09",
                "external": False,
            },
        ],
        "clientToken": None,
    }


@pytest.fixture()
def mock_associate_resource_share_request(mock_associate_resource_share_response):
    return unittest.mock.MagicMock(return_value=mock_associate_resource_share_response)


@pytest.fixture()
def mock_send_task_failure_request():
    return unittest.mock.MagicMock(return_value={})


@pytest.fixture()
def mock_send_lambda_callback_failure_request():
    return unittest.mock.MagicMock(return_value={})


@pytest.fixture()
def mock_send_task_success_request():
    return unittest.mock.MagicMock(return_value={})


@pytest.fixture()
def mock_send_lambda_callback_success_request():
    return unittest.mock.MagicMock(return_value={})


@pytest.fixture()
def mock_moto_error_calls(
    mock_associate_resource_share_request,
    mock_send_task_failure_request,
    mock_send_task_success_request,
    mock_send_lambda_callback_failure_request,
    mock_send_lambda_callback_success_request,
    mocked_modify_image_attribute_request,
):
    invocations = {
        "AssociateResourceShare": mock_associate_resource_share_request,
        "SendTaskFailure": mock_send_task_failure_request,
        "SendTaskSuccess": mock_send_task_success_request,
        "SendDurableExecutionCallbackSuccess": mock_send_lambda_callback_success_request,
        "SendDurableExecutionCallbackFailure": mock_send_lambda_callback_failure_request,
        "ModifyImageAttribute": mocked_modify_image_attribute_request,
    }

    def _interceptor(self, operation_name, kwarg):
        if operation_name in invocations:
            return invocations[operation_name](**kwarg)

        return orig(self, operation_name, kwarg)

    with unittest.mock.patch("botocore.client.BaseClient._make_api_call", new=_interceptor):
        yield invocations


@pytest.fixture
def mocked_modify_image_attribute_request(mocked_modify_image_attribute_response):
    return unittest.mock.MagicMock(return_value=mocked_modify_image_attribute_response)


@pytest.fixture
def mocked_modify_image_attribute_response():
    return {
        "ResponseMetadata": {
            "...": "...",
        },
    }


@pytest.fixture()
def mock_s3_bucket_name():
    return "test-bucket"


@pytest.fixture()
def mock_s3_bucket(mock_s3_client, mock_s3_bucket_name):
    return mock_s3_client.create_bucket(
        Bucket=mock_s3_bucket_name,
        CreateBucketConfiguration={
            "LocationConstraint": "eu-central-1",
        },
    )
