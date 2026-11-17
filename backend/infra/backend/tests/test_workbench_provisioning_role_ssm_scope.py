import fnmatch

import aws_cdk
import pytest
from aws_cdk.assertions import Template

from infra import config
from infra.usecase.product_publishing_enablement_app_stack import (
    ProductPublishingEnablementAppStack,
    _top_level_parameter_namespace,
)

ACCOUNT = "111111111111"
REGION = "us-east-1"
TOKENS = {"AWS::Partition": "aws", "AWS::AccountId": ACCOUNT}


def _render(value) -> str:
    # Resolve the Fn::Join / Ref tokens CDK emits for Aws.PARTITION and Aws.ACCOUNT_ID.
    if isinstance(value, str):
        return value
    if "Ref" in value:
        return TOKENS[value["Ref"]]
    if "Fn::Join" in value:
        separator, parts = value["Fn::Join"]
        return separator.join(_render(part) for part in parts)
    raise ValueError(f"Unsupported CloudFormation intrinsic in policy resource: {value!r}")


def _build_stack(environment_config: dict) -> ProductPublishingEnablementAppStack:
    app_config = config.AppConfig(
        account=ACCOUNT,
        region=REGION,
        environment="dev",
        web_app_account="222222222222",
        component_name="product-publishing-enablement",
        environment_config=environment_config,
        component_specific=config.product_publishing_enablement_app_config["dev"],
    )
    return ProductPublishingEnablementAppStack(
        aws_cdk.App(),
        "ProductPublishingEnablementTest",
        app_config=app_config,
        image_service_account_id="333333333333",
        catalog_service_account_id="444444444444",
        web_application_account="222222222222",
        env=aws_cdk.Environment(account=ACCOUNT, region=REGION),
    )


@pytest.fixture(scope="module")
def get_parameter_resources() -> list[str]:
    stack = _build_stack(config.env_config["dev"])
    policies = Template.from_stack(stack).find_resources(
        "AWS::IAM::Policy", {"Properties": {"PolicyName": "WorkbenchWebAppProvisioningRolePolicy"}}
    )
    (policy,) = policies.values()
    resources = []
    for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
        actions = statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]]
        if "ssm:GetParameter" in actions:
            entries = statement["Resource"] if isinstance(statement["Resource"], list) else [statement["Resource"]]
            resources += [_render(entry) for entry in entries]
    return resources


def _allowed(resources: list[str], parameter_name: str) -> bool:
    arn = f"arn:aws:ssm:{REGION}:{ACCOUNT}:parameter{parameter_name}"
    return any(fnmatch.fnmatchcase(arn, pattern) for pattern in resources)


def test_provisioning_role_can_read_the_spoke_vpc_id_parameter(get_parameter_resources):
    # Read before every workbench launch, so the scoped parameter list has to include it.
    assert _allowed(get_parameter_resources, config.env_config["dev"]["spoke-account-vpc-id-param-name"])


def test_provisioning_role_can_read_the_workbench_ssh_key_parameter(get_parameter_resources):
    # The SSH key download reads the path AWS::EC2::KeyPair writes: /ec2/keypair/<key-pair-id>.
    assert _allowed(get_parameter_resources, "/ec2/keypair/key-0123456789abcdef0")


def test_provisioning_role_get_parameter_stays_scoped(get_parameter_resources):
    assert "*" not in get_parameter_resources
    assert not _allowed(get_parameter_resources, "/other-team/secret")
    assert all(f":{ACCOUNT}:parameter/" in resource for resource in get_parameter_resources)


@pytest.mark.parametrize("parameter_name", ["", "/", "/workbench", "workbench", "//vpc-id", "/workbench//vpc-id"])
def test_namespace_rejects_names_its_scope_would_not_cover(parameter_name):
    # An empty namespace would become parameter//*; a single segment would not be covered by /<ns>/*.
    with pytest.raises(ValueError):
        _top_level_parameter_namespace(parameter_name)


@pytest.mark.parametrize(
    ("parameter_name", "namespace"),
    [("/workbench/vpc/vpc-id", "/workbench"), ("workbench/vpc-id", "/workbench"), ("/a/b/", "/a")],
)
def test_namespace_is_the_first_path_segment(parameter_name, namespace):
    assert _top_level_parameter_namespace(parameter_name) == namespace


def test_stack_synth_fails_on_an_invalid_vpc_parameter_name():
    with pytest.raises(ValueError, match="spoke|namespace"):
        _build_stack({**config.env_config["dev"], "spoke-account-vpc-id-param-name": "/"})


def test_render_reports_unknown_intrinsics():
    with pytest.raises(ValueError, match="Fn::Sub"):
        _render({"Fn::Sub": "arn:${AWS::Partition}:ssm"})
