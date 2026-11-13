"""Unit tests for McpGatewayAgentcoreStack.

The shared fixture synthesises with no bounded-context targets, which keeps most
checks independent of the other stacks. A focused test supplies one fake context
to verify the exact schema passed into the bucket deployment source.
"""

import hashlib
import json

import aws_cdk
import pytest
from aws_cdk import assertions
from aws_cdk import aws_s3_deployment as s3deploy

from infra import config, constants
from infra.backend import mcp_gateway_agentcore_app_stack
from infra.helpers import mcp_openapi_transform


def _app_config() -> config.AppConfig:
    return config.AppConfig(
        account="111111111111",
        region="us-east-1",
        environment=config.Environment.dev,
        web_app_account="111111111111",
        component_name=constants.MCP_AGENTCORE_COMPONENT_NAME,
        environment_config=config.env_config["dev"],
        component_specific=config.mcp_gateway_agentcore_app_config["dev"],
    )


@pytest.fixture(name="template")
def template_fixture() -> assertions.Template:
    # Skip Lambda asset bundling: these tests only inspect the template, and bundling needs
    # rsync, which the CI image (backend-infra-test-job) does not have.
    app = aws_cdk.App(context={"aws:cdk:bundling-stacks": []})
    app_config = _app_config()
    stack = mcp_gateway_agentcore_app_stack.McpGatewayAgentcoreStack(
        app,
        "McpGatewayAgentcoreStack",
        app_config=app_config,
        enabled_stacks=[],
        stack_name=app_config.format_base_resource_name(constants.MCP_AGENTCORE_COMPONENT_NAME),
        env=aws_cdk.Environment(account=app_config.account, region=app_config.region),
    )
    return assertions.Template.from_stack(stack)


def test_gateway_log_group_is_encrypted_with_a_rotating_customer_managed_key(template):
    # The gateway's APPLICATION_LOGS can carry request/response bodies.
    log_groups = template.find_resources("AWS::Logs::LogGroup")
    gateway_log_groups = [
        lg for lg in log_groups.values() if "APPLICATION_LOGS" in str(lg["Properties"].get("LogGroupName", ""))
    ]
    assert len(gateway_log_groups) == 1
    kms_ref = gateway_log_groups[0]["Properties"]["KmsKeyId"]["Fn::GetAtt"][0]

    key = template.to_json()["Resources"][kms_ref]
    assert key["Type"] == "AWS::KMS::Key"
    assert key["Properties"]["EnableKeyRotation"] is True


def test_logs_service_can_use_the_gateway_log_key(template):
    # The CloudWatch Logs principal in a key policy is REGIONAL. Asserting the exact
    # principal, not Match.any_value(), is the point: a global "logs.<url suffix>"
    # principal never matches, so the log group silently fails to ingest.
    template.has_resource_properties(
        "AWS::KMS::Key",
        {
            "KeyPolicy": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                "Principal": {
                                    "Service": {
                                        "Fn::Join": [
                                            "",
                                            ["logs.us-east-1.", {"Ref": "AWS::URLSuffix"}],
                                        ]
                                    }
                                },
                                "Condition": {
                                    "ArnEquals": assertions.Match.object_like(
                                        {"kms:EncryptionContext:aws:logs:arn": assertions.Match.any_value()}
                                    )
                                },
                            }
                        )
                    ]
                )
            }
        },
    )


def test_gateway_role_is_assumable_only_by_this_accounts_own_gateways(template):
    """Without source conditions the bedrock-agentcore service principal is a confused
    deputy: any AgentCore gateway in any account could have the service assume this role."""
    roles = template.find_resources("AWS::IAM::Role")
    agentcore_roles = [
        r
        for r in roles.values()
        if any(
            s.get("Principal", {}).get("Service") == "bedrock-agentcore.amazonaws.com"
            for s in r["Properties"]["AssumeRolePolicyDocument"]["Statement"]
        )
    ]
    assert len(agentcore_roles) == 1
    statement = next(
        s
        for s in agentcore_roles[0]["Properties"]["AssumeRolePolicyDocument"]["Statement"]
        if s.get("Principal", {}).get("Service") == "bedrock-agentcore.amazonaws.com"
    )
    condition = statement["Condition"]
    assert condition["StringEquals"]["aws:SourceAccount"] == "111111111111"
    source_arn = condition["ArnLike"]["aws:SourceArn"]
    assert "bedrock-agentcore" in str(source_arn)
    assert str(source_arn).rstrip("'\"]} ").endswith("-*") or "-*" in str(source_arn)


def test_interceptor_can_be_invoked_only_by_this_accounts_own_gateways(template):
    """Same confused-deputy gap on the Lambda resource policy."""
    permissions = template.find_resources("AWS::Lambda::Permission")
    service_grants = [
        p for p in permissions.values() if p["Properties"].get("Principal") == "bedrock-agentcore.amazonaws.com"
    ]
    assert len(service_grants) == 1
    props = service_grants[0]["Properties"]
    assert props["SourceAccount"] == "111111111111"
    assert "bedrock-agentcore" in str(props["SourceArn"])
    assert "-*" in str(props["SourceArn"])


def test_gateway_accepts_only_its_own_oidc_client(template):
    gateway = template.find_resources("AWS::BedrockAgentCore::Gateway")
    assert len(gateway) == 1
    props = list(gateway.values())[0]["Properties"]
    assert props["AuthorizerType"] == "CUSTOM_JWT"
    allowed = props["AuthorizerConfiguration"]["CustomJWTAuthorizer"]["AllowedClients"]
    assert len(allowed) == 1


def test_stack_creates_no_cognito_client_of_its_own(template):
    # The client is created by the frontend stack from its AdditionalAppClients
    # config; this stack only reads the id from SSM. Asserting the absence keeps
    # a future change from quietly reintroducing a second client-creation path.
    template.resource_count_is("AWS::Cognito::UserPoolClient", 0)


def test_gateway_is_protected_by_waf(template):
    template.resource_count_is("AWS::WAFv2::WebACLAssociation", 1)


@pytest.mark.parametrize(
    "logical_id,resource_type",
    [
        ("GatewayLogs64F6314F", "AWS::Logs::LogGroup"),
        ("SpecBucket3C1FD802", "AWS::S3::Bucket"),
    ],
)
def test_named_resources_keep_their_deployed_logical_ids(template, logical_id, resource_type):
    """Both resources have fixed physical names. A new logical id makes CloudFormation create
    the replacement first, which fails on existing deployments because the old resource still
    holds the name. Change these only together with a migration plan."""
    resources = template.to_json()["Resources"]
    assert logical_id in resources
    assert resources[logical_id]["Type"] == resource_type


def test_stack_passes_exact_transformed_spec_to_json_data(mocker):
    app = aws_cdk.App(context={"aws:cdk:bundling-stacks": []})
    app_config = _app_config()
    bounded_context_stack = aws_cdk.Stack(app, "WidgetsStack")
    bounded_context_stack.bounded_context = "widgets"
    source_spec = {
        "openapi": "3.0.1",
        "info": {"title": "Widgets", "version": "1.0"},
        "paths": {
            "/widgets": {
                "parameters": [
                    {
                        "name": "mode",
                        "in": "query",
                        "description": "The update strategy for returned widgets.",
                        "schema": {
                            "type": "string",
                            "enum": ["merge", "replace"],
                        },
                    }
                ],
                "get": {
                    "operationId": "ListWidgets",
                    "description": (
                        "Lists the widgets available to the current project and returns "
                        "the documented fields needed to select the next workflow action."
                    ),
                },
            }
        },
    }
    base_url = "https://example.com/widgets"
    expected = mcp_openapi_transform.transform(source_spec, base_url)
    expected_key = (
        "widgets-"
        + hashlib.sha256(json.dumps(expected, sort_keys=True, default=str).encode()).hexdigest()[:12]
        + ".json"
    )
    mocker.patch.object(
        mcp_gateway_agentcore_app_stack.McpGatewayAgentcoreStack,
        "_load_source_spec",
        return_value=source_spec,
    )
    mocker.patch.object(
        mcp_gateway_agentcore_app_stack.McpGatewayAgentcoreStack,
        "_resolve_base_url",
        return_value=base_url,
    )
    json_data = mocker.spy(s3deploy.Source, "json_data")

    mcp_gateway_agentcore_app_stack.McpGatewayAgentcoreStack(
        app,
        "McpGatewayWithTargetStack",
        app_config=app_config,
        enabled_stacks=[bounded_context_stack],
        stack_name="mcp-gateway-with-target-test",
        env=aws_cdk.Environment(account=app_config.account, region=app_config.region),
    )

    json_data.assert_called_once_with(expected_key, expected)


def test_redirect_uris_pass_the_frontend_app_client_validation():
    """deploy.sh registers these as the mcp-gateway-agentcore client's CallbackUrls,
    and frontend/infrastructure/lib/app-config.ts rejects any URL that is not https
    or http://localhost (Cognito's own rule). One bad entry fails the frontend deploy."""
    import re

    allowed = re.compile(r"^(?:https://|http://localhost(?:[:/]|$))")
    assert constants.MCP_GATEWAY_OAUTH_REDIRECT_URIS
    for uri in constants.MCP_GATEWAY_OAUTH_REDIRECT_URIS:
        assert allowed.match(uri) and "#" not in uri, uri
    # The printed Kiro and Claude configs use the base port; it must be registered.
    assert f"http://localhost:{constants.MCP_GATEWAY_OAUTH_CALLBACK_PORT}" in constants.MCP_GATEWAY_OAUTH_REDIRECT_URIS
