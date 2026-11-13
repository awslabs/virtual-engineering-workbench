import aws_cdk
from aws_cdk.assertions import Template

from app.shared.api import bounded_contexts
from infra import config
from infra.backend.packaging_app_stack import PACKAGING_MARKETPLACE_LICENSE_MANAGER_ACTIONS
from infra.backend.publishing_app_stack import (
    AMI_SHARING_LICENSE_MANAGER_ACTIONS,
    API_LICENSE_MANAGER_ACTIONS,
    PublishingAppStack,
)


def _publishing_template() -> dict:
    app = aws_cdk.App()
    app_config = config.AppConfig(
        account="111111111111",
        region="us-east-1",
        environment="dev",
        web_app_account="111111111111",
        image_service_account="111111111111",
        catalog_service_account="111111111111",
        component_name=bounded_contexts.BoundedContext.PUBLISHING,
        environment_config=config.env_config["dev"],
        component_specific=config.publishing_app_config["dev"],
    )
    stack = PublishingAppStack(
        app,
        "PublishingAppStack",
        app_config=app_config,
        custom_api_domain="",
        env=aws_cdk.Environment(account="111111111111", region="us-east-1"),
    )
    return Template.from_stack(stack).to_json()


def _actions_for_lambda(template: dict, function_name: str) -> set[str]:
    resources = template["Resources"]
    function = next(
        resource
        for resource in resources.values()
        if resource["Type"] == "AWS::Lambda::Function" and resource["Properties"].get("FunctionName") == function_name
    )
    role_id = function["Properties"]["Role"]["Fn::GetAtt"][0]
    actions: set[str] = set()
    for resource in resources.values():
        if resource["Type"] != "AWS::IAM::Policy":
            continue
        if {"Ref": role_id} not in resource["Properties"].get("Roles", []):
            continue
        for statement in resource["Properties"]["PolicyDocument"]["Statement"]:
            action = statement.get("Action", [])
            actions.update([action] if isinstance(action, str) else action)
    return actions


def test_packaging_discovery_license_manager_permissions_are_minimal():
    assert set(PACKAGING_MARKETPLACE_LICENSE_MANAGER_ACTIONS) == {
        "license-manager:ListReceivedLicenses",
        "license-manager:GetServiceSettings",
    }


def test_publishing_api_license_manager_permissions_are_minimal():
    assert set(API_LICENSE_MANAGER_ACTIONS) == {
        "license-manager:CreateGrant",
        "license-manager:ListDistributedGrants",
    }


def test_ami_sharing_has_license_distribution_readiness_permissions():
    assert set(AMI_SHARING_LICENSE_MANAGER_ACTIONS) == {
        "license-manager:CreateGrant",
        "license-manager:ListDistributedGrants",
        "license-manager:GetServiceSettings",
        "organizations:DescribeOrganization",
        "ram:GetResourceShares",
    }


def test_synthesized_lambda_policies_have_the_expected_license_manager_scope():
    template = _publishing_template()
    api_actions = _actions_for_lambda(template, "proserve-wb-publishing-api-dev")
    ami_sharing_actions = _actions_for_lambda(template, "proserve-wb-publishing-ami-sharing-dev")
    relevant_prefixes = ("license-manager:", "organizations:", "ram:")

    assert {action for action in api_actions if action.startswith(relevant_prefixes)} == set(
        API_LICENSE_MANAGER_ACTIONS
    )
    assert {action for action in ami_sharing_actions if action.startswith(relevant_prefixes)} == set(
        AMI_SHARING_LICENSE_MANAGER_ACTIONS
    )
