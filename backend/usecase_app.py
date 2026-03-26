#!/usr/bin/env python3
import aws_cdk
import cdk_nag

from infra import config
from infra.usecase import (
    prerequisites_app_stack,
    product_publishing_enablement_app_stack,
    provisioning_enablement_stack,
    usecase_app_stack,
)

app = aws_cdk.App()

# Required tags for all resources
required_tags = [
    {"Key": "Application", "Value": "VEW"},
    {"Key": "vew:cost-category", "Value": "shared"},
]

# Apply required tags to all resources in the app
# for tag in required_tags:
# aws_cdk.Tags.of(app).add(tag["Key"], tag["Value"])

environment = app.node.try_get_context("environment")
prerequisites = app.node.try_get_context("prerequisites")

# Define base config
base_config = config.BaseConfig(
    account=app.node.try_get_context("account"),
    web_app_account=app.node.try_get_context("account"),
    environment=environment,
    region=app.node.try_get_context("region"),
)

# Define app configs
prerequisites_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="prerequisites",
    component_specific=config.prerequisites_app_config[environment],
    environment_config=config.env_config[environment],
)

usecase_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="usecase",
    environment_config=config.env_config[environment],
    component_specific=config.usecase_app_config[environment],
)

product_publishing_enablement_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="product-publishing-enablement",
    environment_config=config.env_config[environment],
    component_specific=config.product_publishing_enablement_app_config[environment],
)

provisioning_enablement_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="provisioning-enablement",
    environment_config=config.env_config[environment],
    component_specific=config.provisioning_enablement_app_config[environment],
)

# Define app stacks
# If more than a prerequisites stack is required
# split this into 2 separate CDK apps
if prerequisites:
    prerequisites_stack = prerequisites_app_stack.PrerequisitesAppStack(
        app,
        "PrerequisitesAppStack",
        prerequisites_app_config,
        env=aws_cdk.Environment(
            account=prerequisites_app_config.account,
            region=prerequisites_app_config.region,
        ),
        stack_name=base_config.format_base_resource_name("prerequisites"),
        web_application_account=app.node.try_get_context("web-application-account-id"),
    )
else:
    product_publishing_enablement_stack = product_publishing_enablement_app_stack.ProductPublishingEnablementAppStack(
        app,
        "ProductPublishingEnablementAppStack",
        app_config=product_publishing_enablement_app_config,
        stack_name=base_config.format_base_resource_name("product-publishing-enablement"),
        env=aws_cdk.Environment(account=usecase_app_config.account, region=usecase_app_config.region),
        image_service_account_id=app.node.try_get_context("image-service-account"),
        catalog_service_account_id=app.node.try_get_context("catalog-service-account"),
        web_application_account=app.node.try_get_context("web-application-account-id"),
    )

    prov_enablement_stack = provisioning_enablement_stack.ProvisioningEnablementStack(
        app,
        "ProvisioningEnablementStack",
        app_config=provisioning_enablement_app_config,
        stack_name=base_config.format_base_resource_name("provisioning-enablement"),
        env=aws_cdk.Environment(
            account=provisioning_enablement_app_config.account,
            region=provisioning_enablement_app_config.region,
        ),
        web_application_account=app.node.try_get_context("web-application-account-id"),
        web_application_region=app.node.try_get_context("web-application-region"),
    )

    usecase_stack = usecase_app_stack.UsecaseAppStack(
        app,
        "UsecaseAppStack",
        app_config=usecase_app_config,
        stack_name=base_config.format_base_resource_name("usecase"),
        env=aws_cdk.Environment(account=usecase_app_config.account, region=usecase_app_config.region),
    )

    usecase_stack.add_dependency(product_publishing_enablement_stack)
    usecase_stack.add_dependency(prov_enablement_stack)

# cdk_nag checks
aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(reports=True, verbose=True))
aws_cdk.Aspects.of(app).add(cdk_nag.NIST80053R4Checks(reports=True, verbose=True))
aws_cdk.Aspects.of(app).add(cdk_nag.NIST80053R5Checks(reports=True, verbose=True))
aws_cdk.Aspects.of(app).add(cdk_nag.PCIDSS321Checks(reports=True, verbose=True))

app.synth()
