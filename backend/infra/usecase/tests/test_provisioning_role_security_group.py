"""The spoke provisioning role must be able to create a user's security group.

ec2:CreateSecurityGroup authorizes against both the new security-group and the
existing vpc. aws:RequestTag is a condition key of the security-group resource only,
so a RequestTag condition on the vpc resource never matches and denies every create.
"""

import pytest
from aws_cdk.assertions import Template

from infra import config
from infra.backend.tests.test_workbench_provisioning_role_ssm_scope import ACCOUNT, _build_stack, _render

OWNER_TAG_CONDITION = {"StringEquals": {"aws:RequestTag/vew:securityGroup:ownerId": "${aws:PrincipalTag/UserId}"}}
SECURITY_GROUP = f"arn:aws:ec2:*:{ACCOUNT}:security-group/*"
VPC = f"arn:aws:ec2:*:{ACCOUNT}:vpc/*"


@pytest.fixture(scope="module")
def create_security_group_statements() -> list[dict]:
    policies = Template.from_stack(_build_stack(config.env_config["dev"])).find_resources(
        "AWS::IAM::Policy", {"Properties": {"PolicyName": "WorkbenchWebAppProvisioningRolePolicy"}}
    )
    (policy,) = policies.values()
    found = []
    for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
        actions = statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]]
        if "ec2:CreateSecurityGroup" in actions:
            resources = statement["Resource"] if isinstance(statement["Resource"], list) else [statement["Resource"]]
            found.append({**statement, "Resource": [_render(resource) for resource in resources]})
    return found


def test_security_group_create_requires_the_caller_as_owner(create_security_group_statements):
    (statement,) = [s for s in create_security_group_statements if SECURITY_GROUP in s["Resource"]]
    assert statement["Effect"] == "Allow"
    assert statement["Resource"] == [SECURITY_GROUP]
    assert statement["Condition"] == OWNER_TAG_CONDITION


def test_vpc_leg_of_security_group_create_has_no_request_tag_condition(create_security_group_statements):
    (statement,) = [s for s in create_security_group_statements if VPC in s["Resource"]]
    assert statement["Effect"] == "Allow"
    assert statement["Resource"] == [VPC]
    assert "Condition" not in statement


def test_no_request_tag_condition_is_applied_to_a_vpc(create_security_group_statements):
    for statement in create_security_group_statements:
        conditions = str(statement.get("Condition", {}))
        if "aws:RequestTag" in conditions:
            assert VPC not in statement["Resource"]
