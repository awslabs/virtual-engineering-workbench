import json

import aws_cdk
import pytest
from aws_cdk.assertions import Template

from infra import config, constants
from infra.backend import packaging_app_stack
from infra.backend.integration_oauth_stack import IntegrationOauthStack


def test_packaging_s2s_path_is_stable():
    assert constants.CUSTOM_DNS_S2S_API_PATH_PACKAGING == "clients/packaging/v1"


def test_packaging_stack_has_no_reconciliation_entrypoint():
    assert packaging_app_stack.Entrypoint.S2S_API.value == "s2s-api"
    assert "s2s-reconciliation-events" not in {entry.value for entry in packaging_app_stack.Entrypoint}


@pytest.mark.parametrize(
    ("prefix", "expected_scopes"),
    [
        ("recipe.", {"recipe.read", "recipe.write", "recipe.release"}),
        ("pipeline.", {"pipeline.read", "pipeline.write", "pipeline.execute"}),
    ],
)
def test_publishing_scopes_are_available_without_granting_existing_clients_access(prefix, expected_scopes):
    app = aws_cdk.App()
    app_config = config.AppConfig(
        account="111111111111",
        region="eu-west-1",
        environment="dev",
        web_app_account="111111111111",
        image_service_account="222222222222",
        catalog_service_account="333333333333",
        component_name="packaging",
        environment_config=config.env_config["dev"],
        component_specific=config.packaging_app_config["dev"],
    )
    stack = IntegrationOauthStack(
        app,
        "RecipeOAuthTest",
        app_config=app_config,
        env=aws_cdk.Environment(account="111111111111", region="eu-west-1"),
    )
    template = Template.from_stack(stack)
    servers = template.find_resources("AWS::Cognito::UserPoolResourceServer")
    packaging = next(
        server["Properties"] for server in servers.values() if server["Properties"]["Identifier"] == "clients/packaging"
    )
    scopes = {scope["ScopeName"] for scope in packaging["Scopes"]}
    assert expected_scopes <= scopes
    assert "operation.read" not in scopes
    for client in template.find_resources("AWS::Cognito::UserPoolClient").values():
        assert prefix not in json.dumps(client["Properties"].get("AllowedOAuthScopes", []))
        assert "operation.read" not in json.dumps(client["Properties"].get("AllowedOAuthScopes", []))
