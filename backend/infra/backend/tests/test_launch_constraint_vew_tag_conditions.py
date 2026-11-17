"""Verify the spoke and hub launch-constraint roles use VEW-owned tags.

The obsolete create-time aws:RequestTag/aws:cloudformation:stack-name condition must
not reappear.
"""

import aws_cdk
import pytest
from aws_cdk.assertions import Template

from infra import config
from infra.backend.product_publishing_app_stack import ProductPublishingAppStack
from infra.backend.tests.test_workbench_provisioning_role_ssm_scope import ACCOUNT, REGION, _build_stack

VEW_TAG = "vew:provisionedProduct:id"
VEW_TAG_VALUE = "vew-pp-*"
CREATE_ACTIONS = {"ec2:AllocateAddress", "secretsmanager:CreateSecret"}
TEARDOWN_ACTIONS = {
    "ec2:AssociateAddress",
    "ec2:DisassociateAddress",
    "ec2:ReleaseAddress",
    "secretsmanager:DeleteSecret",
    "secretsmanager:TagResource",
    "secretsmanager:UntagResource",
}


def _hub_template() -> Template:
    app_config = config.AppConfig(
        account=ACCOUNT,
        region=REGION,
        environment="dev",
        web_app_account=ACCOUNT,
        component_name="product-publishing",
        environment_config=config.env_config["dev"],
        component_specific=config.product_publishing_app_config["dev"],
    )
    stack = ProductPublishingAppStack(
        aws_cdk.App(),
        "ProductPublishingTest",
        app_config=app_config,
        image_service_account_id="333333333333",
        web_app_account_id=ACCOUNT,
        env=aws_cdk.Environment(account=ACCOUNT, region=REGION),
    )
    return Template.from_stack(stack)


def _spoke_template() -> Template:
    return Template.from_stack(_build_stack(config.env_config["dev"]))


def _launch_constraint_statements(template: Template) -> list[dict]:
    statements = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        document = policy["Properties"]["PolicyDocument"]["Statement"]
        name = policy["Properties"].get("PolicyName", "")
        roles = str(policy["Properties"].get("Roles", ""))
        if "LaunchConstraint" in name or "LaunchConstraint" in roles:
            statements += document
    return statements


def _actions(statement: dict) -> set[str]:
    return set(statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]])


def _granted_on_vew_tag(statements: list[dict], key_kind: str) -> set[str]:
    granted = set()
    for statement in statements:
        condition = statement.get("Condition", {}).get("StringLike", {})
        if statement["Effect"] == "Allow" and condition.get(f"aws:{key_kind}/{VEW_TAG}") == VEW_TAG_VALUE:
            granted |= _actions(statement)
    return granted


@pytest.fixture(scope="module", params=["spoke", "hub"])
def statements(request) -> list[dict]:
    template = _spoke_template() if request.param == "spoke" else _hub_template()
    found = _launch_constraint_statements(template)
    assert found, f"no launch-constraint policy found in the {request.param} stack"
    return found


def test_create_actions_are_granted_on_the_vew_request_tag(statements):
    assert CREATE_ACTIONS <= _granted_on_vew_tag(statements, "RequestTag")


def test_teardown_actions_are_granted_on_the_vew_resource_tag(statements):
    assert TEARDOWN_ACTIONS <= _granted_on_vew_tag(statements, "ResourceTag")


def test_vew_tag_statements_grant_nothing_else(statements):
    assert _granted_on_vew_tag(statements, "ResourceTag") == TEARDOWN_ACTIONS
    assert _granted_on_vew_tag(statements, "RequestTag") - CREATE_ACTIONS <= {"ec2:CreateTags"}


def test_dead_reserved_request_tag_condition_is_absent(statements):
    for statement in statements:
        for condition_values in statement.get("Condition", {}).values():
            assert "aws:RequestTag/aws:cloudformation:stack-name" not in condition_values
