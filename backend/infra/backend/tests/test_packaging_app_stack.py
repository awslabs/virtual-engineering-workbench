"""Synthesised assertions on PackagingAppStack.

The stack is built standalone: it only needs the SNS topic from ProductPackagingAppStack,
so no full app assembly is required. Lambda bundling is skipped via the
`aws:cdk:bundling-stacks` context, as in the other infra tests.
"""

import aws_cdk
import pytest
from aws_cdk import assertions

from infra import config
from infra.backend import packaging_app_stack, product_packaging_app_stack

ACCOUNT = "111111111111"
REGION = "eu-west-1"

_BASE = dict(
    account=ACCOUNT,
    region=REGION,
    environment="dev",
    web_app_account=ACCOUNT,
    image_service_account="222222222222",
    catalog_service_account="333333333333",
)


@pytest.fixture(name="template")
def template_fixture() -> assertions.Template:
    app = aws_cdk.App(context={"aws:cdk:bundling-stacks": []})
    env = aws_cdk.Environment(account=ACCOUNT, region=REGION)
    product_packaging = product_packaging_app_stack.ProductPackagingAppStack(
        app,
        "ProductPackagingAppStack",
        app_config=config.AppConfig(
            **_BASE,
            component_name="product-packaging",
            environment_config=config.env_config["dev"],
            component_specific=config.product_packaging_app_config["dev"],
        ),
        env=env,
        web_application_account=ACCOUNT,
    )
    stack = packaging_app_stack.PackagingAppStack(
        app,
        "PackagingAppStack",
        app_config=config.AppConfig(
            **_BASE,
            component_name="packaging",
            environment_config=config.env_config["dev"],
            component_specific=config.packaging_app_config["dev"],
        ),
        env=env,
        product_packaging_topic=product_packaging.product_packaging_topic,
        custom_api_domain="",
        resource_tags={},
    )
    return assertions.Template.from_stack(stack)


def _lambda_env(template: assertions.Template, name_fragment: str) -> dict:
    for logical_id, function in template.find_resources("AWS::Lambda::Function").items():
        if name_fragment in logical_id.lower():
            return (function["Properties"].get("Environment") or {}).get("Variables", {})
    raise AssertionError(f"No Lambda whose logical id contains {name_fragment!r}")


def test_domain_event_handler_keeps_the_build_logs_bucket(template):
    """The handler reads BUILD_LOGS_S3_BUCKET_NAME (domain_event_handler/config.py) and
    passes it to the Image Builder pipeline service, which omits the s3Logs block when it
    is empty. Dropping the variable turns off build-log delivery silently."""
    variables = _lambda_env(template, "domainevents")
    assert "BUILD_LOGS_S3_BUCKET_NAME" in variables
    assert variables["BUILD_LOGS_S3_BUCKET_NAME"]


def test_stack_grants_no_marketplace_or_license_manager_permissions(template):
    """Packaging has no marketplace or licence-manager client code. Granting those actions
    here would be privilege the stack cannot use."""
    policies = template.find_resources("AWS::IAM::Policy")
    actions = []
    for policy in policies.values():
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            action = statement.get("Action")
            actions.extend(action if isinstance(action, list) else [action])
    granted = {a for a in actions if isinstance(a, str)}
    assert not {a for a in granted if a.startswith("aws-marketplace:")}
    assert not {a for a in granted if a.startswith("license-manager:")}


def test_stack_declares_no_scheduled_jobs_entrypoint(template):
    """There is no scheduled_jobs_handler module in this bounded context, so neither the
    Lambda nor an EventBridge rule targeting it may exist."""
    assert "SCHEDULED" not in packaging_app_stack.Entrypoint.__members__
    assert "scheduled" not in {entry.value for entry in packaging_app_stack.Entrypoint}
    rule_names = [rule["Properties"].get("Name", "") for rule in template.find_resources("AWS::Events::Rule").values()]
    assert not [name for name in rule_names if "marketplace" in str(name).lower()]
