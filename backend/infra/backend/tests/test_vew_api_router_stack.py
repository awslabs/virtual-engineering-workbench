"""Unit tests for VewApiRouterStack.

Three things here are contracts rather than implementation details:

* every route carries the JWT authorizer — the router is internet facing, and an
  unauthorized route is the finding that put this authorizer here;
* the stack creates no SSM parameters. It reads three, but deploy.sh owns the
  ``vew-api-endpoint`` parameter in both deploy modes. A stack-owned parameter
  would make switching modes a CloudFormation failure, and recreating the
  Cognito-owned ones would collide on the parameter name;
* the ``VewApiEndpoint`` output and its export name, since deploy.sh reads that
  output to publish the endpoint the CLI consumes.
"""

import json

import assertpy
import aws_cdk
import pytest
from aws_cdk import assertions

from app.shared.api import bounded_contexts
from infra import config, constants
from infra.backend import vew_api_router_stack

BOUNDED_CONTEXTS = ["projects", "packaging"]

# Matches what backend_app.py passes, so export names and resource names are
# exercised at the values production actually uses.
STACK_NAME = "proserve-wb-vew-api-router-dev"


def _app_config() -> config.AppConfig:
    return config.AppConfig(
        account="111111111111",
        region="us-east-1",
        environment=config.Environment.dev,
        web_app_account="111111111111",
        component_name=constants.VEW_API_ROUTER_COMPONENT_NAME,
        environment_config=config.env_config["dev"],
        component_specific=dict(),
    )


def _build_stack(bounded_contexts=None) -> vew_api_router_stack.VewApiRouterStack:
    app = aws_cdk.App()
    app_config = _app_config()
    return vew_api_router_stack.VewApiRouterStack(
        app,
        "VewApiRouterStack",
        app_config=app_config,
        bounded_contexts=BOUNDED_CONTEXTS if bounded_contexts is None else bounded_contexts,
        stack_name=app_config.format_base_resource_name(constants.VEW_API_ROUTER_COMPONENT_NAME),
        env=aws_cdk.Environment(account=app_config.account, region=app_config.region),
    )


@pytest.fixture(name="stack")
def stack_fixture() -> vew_api_router_stack.VewApiRouterStack:
    return _build_stack()


@pytest.fixture(name="template")
def template_fixture(stack) -> assertions.Template:
    return assertions.Template.from_stack(stack)


def test_stack_name_matches_the_backend_naming_convention(stack):
    # backend_app.py derives this from format_base_resource_name, and the
    # deploy.sh migration block reconstructs the same string to find the stack.
    assertpy.assert_that(stack.stack_name).is_equal_to(STACK_NAME)


def test_creates_a_single_jwt_authorizer(template):
    authorizers = template.find_resources("AWS::ApiGatewayV2::Authorizer")
    assertpy.assert_that(authorizers).is_length(1)
    properties = list(authorizers.values())[0]["Properties"]
    assertpy.assert_that(properties["AuthorizerType"]).is_equal_to("JWT")
    assertpy.assert_that(properties["Name"]).is_equal_to("proserve-wb-vew-cli-authorizer-dev")


def test_authorizer_audience_is_the_vew_cli_app_client(template):
    # The CLI sends a Cognito access token, which carries client_id and no aud.
    # API Gateway falls back to validating client_id against the audience list,
    # so the audience must be the vew-cli app client id.
    authorizers = template.find_resources("AWS::ApiGatewayV2::Authorizer")
    jwt_config = list(authorizers.values())[0]["Properties"]["JwtConfiguration"]
    assertpy.assert_that(jwt_config["Audience"]).is_length(1)

    # Resolved from SSM at deploy time, so the template holds a Ref to the
    # generated CloudFormation parameter rather than a literal. The path is the
    # per-client parameter the frontend stack publishes for each
    # AdditionalAppClients entry, so registering the client is a config change
    # rather than a code change.
    audience_ref = jwt_config["Audience"][0]["Ref"]
    parameters = template.to_json()["Parameters"]
    assertpy.assert_that(parameters[audience_ref]["Default"]).is_equal_to("/proserve-wb-ui-dev/app-client-id/vew-cli")


def test_authorizer_issuer_is_built_from_the_user_pool(template):
    authorizers = template.find_resources("AWS::ApiGatewayV2::Authorizer")
    jwt_config = list(authorizers.values())[0]["Properties"]["JwtConfiguration"]
    issuer_parts = jwt_config["Issuer"]["Fn::Join"][1]

    assertpy.assert_that(issuer_parts[0]).is_equal_to("https://cognito-idp.us-east-1.amazonaws.com/")

    parameters = template.to_json()["Parameters"]
    assertpy.assert_that(parameters[issuer_parts[1]["Ref"]]["Default"]).is_equal_to("/proserve-wb-ui-dev/user-pool-id")


def test_every_route_requires_the_authorizer(template):
    # The whole point of the stack carrying an authorizer: no route may be open.
    routes = template.find_resources("AWS::ApiGatewayV2::Route")
    assertpy.assert_that(routes).is_length(len(BOUNDED_CONTEXTS))

    for route in routes.values():
        properties = route["Properties"]
        assertpy.assert_that(properties["AuthorizationType"]).is_equal_to("JWT")
        assertpy.assert_that(properties).contains_key("AuthorizerId")


def test_one_proxy_route_per_bounded_context(template):
    routes = template.find_resources("AWS::ApiGatewayV2::Route")
    route_keys = sorted(route["Properties"]["RouteKey"] for route in routes.values())
    assertpy.assert_that(route_keys).is_equal_to(sorted(f"ANY /{bc}/{{proxy+}}" for bc in BOUNDED_CONTEXTS))


def test_reads_each_bounded_context_api_url_from_ssm(template):
    parameters = template.to_json()["Parameters"]
    defaults = [p.get("Default") for p in parameters.values()]

    for bounded_context in BOUNDED_CONTEXTS:
        assertpy.assert_that(defaults).contains(f"/proserve-wb-{bounded_context}-api-dev/api/url")


def test_creates_no_ssm_parameters(template):
    # deploy.sh owns /<app-name>-ui-<env>/vew-api-endpoint in both deploy
    # modes; its APP_NAME variable already includes the -ui suffix. The Cognito
    # parameters belong to the frontend user pool construct. Creating any
    # of them here would collide on the parameter name at deploy time while
    # passing synth.
    assertpy.assert_that(template.find_resources("AWS::SSM::Parameter")).is_empty()


def test_exposes_the_endpoint_output_deploy_sh_reads(template):
    # deploy.sh Phase 7b reads this output by key and copies it into the SSM
    # parameter the CLI consumes, so both the key and the export name matter.
    outputs = template.to_json()["Outputs"]
    assertpy.assert_that(outputs).contains_key("VewApiEndpoint")
    assertpy.assert_that(outputs["VewApiEndpoint"]["Export"]["Name"]).is_equal_to(f"{STACK_NAME}-VewApiEndpoint")


def test_exposes_the_routed_bounded_contexts_output(template):
    outputs = template.to_json()["Outputs"]
    assertpy.assert_that(outputs["VewApiRoutedBoundedContexts"]["Value"]).is_equal_to(",".join(BOUNDED_CONTEXTS))
    assertpy.assert_that(outputs["VewApiRoutedBoundedContexts"]["Export"]["Name"]).is_equal_to(
        f"{STACK_NAME}-VewApiRoutedBoundedContexts"
    )


def test_http_api_is_named_for_the_component(template):
    template.has_resource_properties("AWS::ApiGatewayV2::Api", {"Name": STACK_NAME})


def test_access_logging_is_enabled_on_the_default_stage(template):
    stages = template.find_resources("AWS::ApiGatewayV2::Stage")
    assertpy.assert_that(stages).is_length(1)
    properties = list(stages.values())[0]["Properties"]
    assertpy.assert_that(properties).contains_key("AccessLogSettings")

    log_format = json.loads(properties["AccessLogSettings"]["Format"])
    assertpy.assert_that(log_format).contains_key("requestId", "routeKey", "status")


def test_access_log_group_follows_the_backend_convention(template):
    # Explicit name, retained on stack deletion, and the same retention the other
    # backend API access log groups use.
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "proserve-wb-vew-api-router-access-log-group-dev",
            "RetentionInDays": 60,
        },
    )
    log_groups = template.find_resources("AWS::Logs::LogGroup")
    assertpy.assert_that(list(log_groups.values())[0]["DeletionPolicy"]).is_equal_to("Retain")


def test_rejects_an_empty_bounded_context_list():
    # A router with no routes would deploy happily and answer nothing.
    assertpy.assert_that(_build_stack).raises(ValueError).when_called_with(bounded_contexts=[])


def test_routed_contexts_come_from_the_bounded_context_enum():
    # The list backend_app.py passes is derived from BoundedContext rather than
    # spelled out, so a rename cannot silently stop routing a context. This asserts
    # the derivation still holds.
    known = {bc.value for bc in bounded_contexts.BoundedContext}
    assertpy.assert_that(set(constants.VEW_API_ROUTER_BOUNDED_CONTEXTS)).is_subset_of(known)


def test_authorization_context_is_not_routed():
    # AUTHORIZATION backs the Cedar authorizer the other contexts invoke; it has no
    # user-facing API the CLI calls, so routing it would expose an endpoint with no
    # caller.
    assertpy.assert_that(constants.VEW_API_ROUTER_BOUNDED_CONTEXTS).does_not_contain(
        bounded_contexts.BoundedContext.AUTHORIZATION.value
    )
