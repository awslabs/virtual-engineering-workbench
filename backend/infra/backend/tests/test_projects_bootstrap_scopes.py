import json

import aws_cdk
from aws_cdk.assertions import Template

from infra import config
from infra.backend.integration_oauth_stack import IntegrationOauthStack


def test_bootstrap_scope_is_defined_but_not_granted_to_any_provisioned_client():
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
        "ProjectsOAuthTest",
        app_config=app_config,
        env=aws_cdk.Environment(account="111111111111", region="eu-west-1"),
    )
    template = Template.from_stack(stack)
    servers = template.find_resources("AWS::Cognito::UserPoolResourceServer")
    projects = next(
        server["Properties"] for server in servers.values() if server["Properties"]["Identifier"] == "clients/projects"
    )
    # The scope stays defined so a break-glass client can be created by hand for orphan recovery.
    assert "client_assignment.bootstrap" in {scope["ScopeName"] for scope in projects["Scopes"]}
    clients = template.find_resources("AWS::Cognito::UserPoolClient")
    assert len(clients) == 2
    assert not any("PlatformProjectsBootstrap" in key for key in clients)
    for client in clients.values():
        assert "client_assignment.bootstrap" not in json.dumps(client["Properties"]["AllowedOAuthScopes"])
