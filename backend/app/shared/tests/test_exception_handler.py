import assertpy
import pytest
from attr import dataclass
from aws_lambda_powertools.event_handler import api_gateway

from app.shared.middleware import exception_handler


@pytest.fixture
def event_payload():
    return {
        "resource": "/projects/{projectId}/workbenches",
        "path": "/products/projects/cd68168f-bae3-4840-a336-82f9d3c2bc26/workbenches",
        "httpMethod": "POST",
        "headers": {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.5",
            "Authorization": "***",
            "content-type": "application/json",
            "Host": "dev.api.workbench.proserve.com",
            "origin": "http://localhost:3000",
            "referer": "http://localhost:3000/",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:102.0) Gecko/20100101 Firefox/102.0",
            "X-Amzn-Trace-Id": "Root=1-64a7dcce-00c0df8e6f32f719186571b1",
            "X-Forwarded-For": "52.94.133.138",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
        },
        "multiValueHeaders": {},
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": {"projectId": "cd68168f-bae3-4840-a336-82f9d3c2bc26"},
        "stageVariables": None,
        "requestContext": {
            "resourceId": "jy3ato",
            "authorizer": {},
            "resourcePath": "/projects/{projectId}/workbenches",
            "operationName": "ProvisionWorkbench",
            "httpMethod": "POST",
            "extendedRequestId": "Hr9wPHZboAMFp8Q=",
            "requestTime": "07/Jul/2023:09:37:18 +0000",
            "path": "/products/projects/cd68168f-bae3-4840-a336-82f9d3c2bc26/workbenches",
            "accountId": "201223934255",
            "protocol": "HTTP/1.1",
            "stage": "v1",
            "domainPrefix": "dev",
            "requestTimeEpoch": 1688722638026,
            "requestId": "6f9c5d57-0299-437c-ab82-2e19456cf5b0",
            "identity": {},
            "domainName": "dev.api.workbench.proserve.com",
            "apiId": "xxxxxxxxxx",
        },
        "body": '{"maintenanceWindow":"0-240","versionId":"pa-psmypwnpm3urs","targetAccountId":"8017de89-19f7-4242-9f7c-bad08e0fa0dd","productId":"prod-hpstkrj4ozbem","provisioningParameters":[{"value":"/workbench/vpc/privatesubnet-id-balanced","key":"SubnetIdSSM"},{"value":"/workbench/autosar/adaptive/ami-id/v1-4-x","key":"AmiIdSSM"},{"value":"/workbench/vpc/vpc-id","key":"VpcIdSSM"}]}',
        "isBase64Encoded": False,
    }


@pytest.fixture
def cors_config():
    return api_gateway.CORSConfig(
        **{
            "allow_origin": "*",
            "expose_headers": [],
            "allow_headers": ["Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-amz-security-token"],
            "max_age": 100,
            "allow_credentials": True,
        }
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


def test_when_throws_user_exception_should_add_cors_headers(lambda_context, event_payload, cors_config):
    # ARRANGE
    app = api_gateway.ApiGatewayResolver(cors=cors_config, strip_prefixes=["/products"])

    @app.post("/projects/<project_id>/workbenches")
    def test_impl(project_id):
        raise Exception()

    @exception_handler.handle_exceptions(
        user_exceptions=[Exception], cors_config=cors_config
    )  # TODO: add custom user exceptions to the array
    def test_handler(evt, ctx):
        return app.resolve(evt, ctx)

    # ACT
    resp = test_handler(event_payload, lambda_context)

    # ASSERT
    assertpy.assert_that(resp.get("statusCode")).is_equal_to(400)
    assertpy.assert_that(resp).contains("headers")
    assertpy.assert_that(resp.get("headers")).is_equal_to(
        {
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Headers": "Authorization,Content-Type,Content-Type,X-Amz-Date,Authorization,X-Api-Key,x-amz-security-token,X-Amz-Date,X-Amz-Security-Token,X-Api-Key",
            "Access-Control-Allow-Origin": "http://localhost:3000",
            "Access-Control-Max-Age": "100",
        }
    )
