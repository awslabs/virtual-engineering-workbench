"""Infra assertions for the Marketplace agreement event listener.

Covers the IAM grant the AMI-only admission gate needs.
The gate is handler-side rather than rule-side because no buyer-side
``aws.agreement-marketplace`` event carries a product type, so the Lambda
has to call ``DescribeAgreement`` and therefore needs permission to.
"""

import json

import aws_cdk
import pytest
from aws_cdk.assertions import Template

from infra import config
from infra.backend import packaging_app_stack, product_packaging_app_stack

ACCOUNT = "111111111111"
REGION = "us-east-1"


@pytest.fixture(scope="module")
def packaging_template() -> Template:
    # Skip asset bundling: these tests assert IAM only, and bundling the
    # shared layer needs rsync, which the CI image does not have.
    app = aws_cdk.App(context={"aws:cdk:bundling-stacks": []})
    shared = dict(
        environment="dev",
        web_app_account=ACCOUNT,
        image_service_account="222222222222",
        catalog_service_account="333333333333",
    )
    product_packaging_config = config.AppConfig(
        account=ACCOUNT,
        region=REGION,
        component_name="product-packaging",
        environment_config=config.env_config["dev"],
        component_specific=config.product_packaging_app_config["dev"],
        **shared,
    )
    packaging_config = config.AppConfig(
        account=ACCOUNT,
        region=REGION,
        component_name="packaging",
        environment_config=config.env_config["dev"],
        component_specific=config.packaging_app_config["dev"],
        **shared,
    )
    env = aws_cdk.Environment(account=ACCOUNT, region=REGION)
    product_packaging_stack = product_packaging_app_stack.ProductPackagingAppStack(
        app,
        "ProductPackagingAppStack",
        app_config=product_packaging_config,
        env=env,
        web_application_account=ACCOUNT,
    )
    stack = packaging_app_stack.PackagingAppStack(
        app,
        "PackagingAppStack",
        app_config=packaging_config,
        env=env,
        product_packaging_topic=product_packaging_stack.product_packaging_topic,
        custom_api_domain="",
        provision_private_endpoint=False,
        vpc_endpoint=None,
    )
    return Template.from_stack(stack)


def _statements_for_marketplace_event_role(template: Template) -> list[dict]:
    """IAM statements attached to the marketplace-agreement-events function."""
    statements = []
    for policy in template.find_resources("AWS::IAM::Policy").values():
        roles = json.dumps(policy["Properties"].get("Roles", []))
        if "marketplaceagreementevents" not in roles.replace("-", "").lower():
            continue
        statements.extend(policy["Properties"]["PolicyDocument"]["Statement"])
    return statements


def test_marketplace_event_listener_can_describe_agreements(packaging_template):
    """The admission gate calls DescribeAgreement, so the grant must exist.

    Without it every agreement event raises and, after Lambda's
    asynchronous retries, lands on the function's dead-letter queue, because
    the gate deliberately refuses to guess a product type it cannot read.
    """
    actions = set()
    for statement in _statements_for_marketplace_event_role(packaging_template):
        action = statement.get("Action", [])
        actions.update([action] if isinstance(action, str) else action)

    assert "aws-marketplace:DescribeAgreement" in actions


def test_marketplace_event_listener_gets_no_other_marketplace_actions(packaging_template):
    """The listener is a pure observer: read one agreement, publish, stop.

    Guards against the procurement action set (CreateAgreementRequest,
    AcceptAgreementRequest, CancelAgreement, ...) being copied onto this
    role, which would give an event handler the ability to move money.
    """
    marketplace_actions = set()
    for statement in _statements_for_marketplace_event_role(packaging_template):
        action = statement.get("Action", [])
        for entry in [action] if isinstance(action, str) else action:
            if isinstance(entry, str) and entry.startswith("aws-marketplace:"):
                marketplace_actions.add(entry)

    assert marketplace_actions == {"aws-marketplace:DescribeAgreement"}
