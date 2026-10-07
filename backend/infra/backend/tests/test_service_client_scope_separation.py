import json

import aws_cdk
from aws_cdk.assertions import Template

from infra import config
from infra.backend.integration_oauth_stack import IntegrationOauthStack


def test_assignment_management_and_packaging_scopes_are_separate():
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
        "AssignmentScopesTest",
        app_config=app_config,
        env=aws_cdk.Environment(account="111111111111", region="eu-west-1"),
    )
    template = Template.from_stack(stack)
    servers = template.find_resources("AWS::Cognito::UserPoolResourceServer")
    projects_server_id = next(
        resource_id
        for resource_id, server in servers.items()
        if server["Properties"]["Identifier"] == "clients/projects"
    )
    packaging_server_id = next(
        resource_id
        for resource_id, server in servers.items()
        if server["Properties"]["Identifier"] == "clients/packaging"
    )
    clients = {
        client["Properties"]["ClientName"]: client["Properties"]["AllowedOAuthScopes"]
        for client in template.find_resources("AWS::Cognito::UserPoolClient").values()
    }
    assert len(clients) == 3
    management_scopes = next(scopes for name, scopes in clients.items() if "projects-assignment-management" in name)
    assert management_scopes == [
        {"Fn::Join": ["", [{"Ref": projects_server_id}, "/client_assignment.read"]]},
        {"Fn::Join": ["", [{"Ref": projects_server_id}, "/client_assignment.write"]]},
    ]
    sample_scopes = next(scopes for name, scopes in clients.items() if "sample-s2s" in name)
    assert "client_assignment.write" not in json.dumps(sample_scopes)
    assert "/component.write" in json.dumps(sample_scopes)
    for scopes in clients.values():
        serialized = json.dumps(scopes)
        assert not ("client_assignment.write" in serialized and packaging_server_id in serialized)
