"""Unit tests for McpGatewayAgentcoreStack.

Synthesised with no bounded-context targets, which keeps the test independent of
the other stacks while still covering the gateway, its auth, and its logging.
"""

import aws_cdk
import pytest
from aws_cdk import assertions

from infra import config, constants
from infra.backend import mcp_gateway_agentcore_app_stack


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
    template.has_resource_properties(
        "AWS::KMS::Key",
        {
            "KeyPolicy": {
                "Statement": assertions.Match.array_with(
                    [
                        assertions.Match.object_like(
                            {
                                # logs.<url suffix>, rendered as an Fn::Join token.
                                "Principal": {"Service": assertions.Match.any_value()},
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
