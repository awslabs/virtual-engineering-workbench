import aws_cdk
from aws_cdk.assertions import Template

from infra import config, constants
from infra.usecase.provisioning_enablement_stack import ProvisioningEnablementStack

ACCOUNT = "111111111111"
REGION = "eu-west-1"


def _instance_profile_statements() -> list[dict]:
    app = aws_cdk.App()
    app_config = config.AppConfig(
        account=ACCOUNT,
        region=REGION,
        environment="dev",
        web_app_account="222222222222",
        image_service_account="333333333333",
        catalog_service_account="444444444444",
        component_name="provisioning-enablement",
        environment_config=config.env_config["dev"],
        component_specific=config.provisioning_enablement_app_config["dev"],
    )
    stack = ProvisioningEnablementStack(
        app,
        "ProvisioningEnablementTest",
        app_config=app_config,
        web_application_account="222222222222",
        web_application_region=REGION,
        env=aws_cdk.Environment(account=ACCOUNT, region=REGION),
    )
    policies = Template.from_stack(stack).find_resources(
        "AWS::IAM::ManagedPolicy",
        {"Properties": {"ManagedPolicyName": constants.PROVISIONED_PRODUCT_INSTANCE_PROFILE_POLICY}},
    )
    assert len(policies) == 1
    return next(iter(policies.values()))["Properties"]["PolicyDocument"]["Statement"]


def _resolve(value) -> str:
    """Render a synthesized Fn::Join with the pseudo parameters filled in."""
    if isinstance(value, str):
        return value
    if "Ref" in value:
        return {"AWS::Partition": "aws", "AWS::Region": REGION, "AWS::AccountId": ACCOUNT}[value["Ref"]]
    separator, parts = value["Fn::Join"]
    return separator.join(_resolve(part) for part in parts)


def _statements_with(action: str, statements: list[dict]) -> list[dict]:
    return [s for s in statements if action in ([s["Action"]] if isinstance(s["Action"], str) else s["Action"])]


def test_instances_may_modify_only_their_own_metadata_options():
    (statement,) = _statements_with("ec2:ModifyInstanceMetadataOptions", _instance_profile_statements())

    assert statement["Effect"] == "Allow"
    assert statement["Action"] == "ec2:ModifyInstanceMetadataOptions"
    assert _resolve(statement["Resource"]) == f"arn:aws:ec2:{REGION}:{ACCOUNT}:instance/*"
    assert {key: {k: _resolve(v) for k, v in cond.items()} for key, cond in statement["Condition"].items()} == {
        "StringEquals": {"ec2:SourceInstanceARN": f"arn:aws:ec2:{REGION}:{ACCOUNT}:instance/${{ec2:InstanceID}}"}
    }


def test_describe_instances_stays_on_every_instance():
    (statement,) = _statements_with("ec2:DescribeInstances", _instance_profile_statements())

    assert statement["Action"] == "ec2:DescribeInstances"
    assert statement["Resource"] == "*"
    assert "Condition" not in statement


def test_no_instance_profile_statement_grants_a_write_on_every_resource():
    for statement in _instance_profile_statements():
        if statement["Resource"] == "*":
            actions = [statement["Action"]] if isinstance(statement["Action"], str) else statement["Action"]
            assert all(action.split(":")[1].startswith("Describe") for action in actions), statement
