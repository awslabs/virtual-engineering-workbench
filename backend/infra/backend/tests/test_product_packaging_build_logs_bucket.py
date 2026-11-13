import json

import aws_cdk
from aws_cdk.assertions import Template

from infra import config
from infra.backend import product_packaging_app_stack

IMAGE_SERVICE_ACCOUNT = "222222222222"
REGION = "eu-west-1"


def _template() -> Template:
    app = aws_cdk.App()
    app_config = config.AppConfig(
        account=IMAGE_SERVICE_ACCOUNT,
        region=REGION,
        environment="dev",
        web_app_account="111111111111",
        image_service_account=IMAGE_SERVICE_ACCOUNT,
        catalog_service_account="333333333333",
        component_name="product-packaging",
        environment_config=config.env_config["dev"],
        component_specific=config.product_packaging_app_config["dev"],
    )
    stack = product_packaging_app_stack.ProductPackagingAppStack(
        app,
        "ProductPackagingTest",
        app_config=app_config,
        web_application_account="111111111111",
        env=aws_cdk.Environment(account=IMAGE_SERVICE_ACCOUNT, region=REGION),
    )
    return Template.from_stack(stack)


def _build_logs_bucket(template: Template) -> tuple[str, dict]:
    expected_name = config.packaging_app_config["dev"]["build-logs-s3-bucket-name"].format(
        environment="dev", image_service_account_id=IMAGE_SERVICE_ACCOUNT, region=REGION
    )
    buckets = template.find_resources("AWS::S3::Bucket")
    matches = [(lid, res) for lid, res in buckets.items() if res["Properties"].get("BucketName") == expected_name]
    assert len(matches) == 1, f"no bucket named {expected_name}, the name the packaging stack sends Image Builder"
    return matches[0]


def test_build_logs_bucket_expires_objects_after_the_configured_retention():
    _, bucket = _build_logs_bucket(_template())

    retention = config.product_packaging_app_config["dev"]["build-logs-retention-days"]
    rules = bucket["Properties"]["LifecycleConfiguration"]["Rules"]
    assert any(
        rule.get("ExpirationInDays") == retention
        and rule.get("NoncurrentVersionExpiration", {}).get("NoncurrentDays") == retention
        for rule in rules
    )


def test_build_instances_may_only_put_build_logs():
    template = _template()
    logical_id, _ = _build_logs_bucket(template)

    actions = set()
    for policy in template.find_resources("AWS::IAM::Policy").values():
        for statement in policy["Properties"]["PolicyDocument"]["Statement"]:
            if logical_id in json.dumps(statement.get("Resource")):
                granted = statement["Action"]
                actions.update([granted] if isinstance(granted, str) else granted)
    assert "s3:PutObject" in actions
    assert not {action for action in actions if action.startswith(("s3:Get", "s3:Delete", "s3:List"))}
