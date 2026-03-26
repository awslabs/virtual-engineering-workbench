#!/usr/bin/env python3
import aws_cdk
import cdk_nag

from infra import config, constants
from infra.backend import (
    authorization_app_stack,
    catalog_service_regional_stack,
    image_key_app_stack,
    image_sharing_app_stack,
    integration_oauth_stack,
    integration_permissions_stack,
    integration_stack,
    packaging_app_stack,
    prerequisites_app_stack,
    product_packaging_app_stack,
    product_publishing_app_stack,
    projects_app_stack,
    provisioning_app_stack,
    publishing_app_stack,
    security_stack,
    shared_deployment_infrastructure,
)

app = aws_cdk.App()

environment = app.node.try_get_context("environment")
cert_arn = app.node.try_get_context("cert-arn")
custom_domain = app.node.try_get_context("use-custom-domain")
organization_id = app.node.try_get_context("organization-id")
ci_commit_sha = app.node.try_get_context("ci-commit-sha") or "latest"
qualifier = (
    app.node.try_get_context("@aws-cdk/core:bootstrapQualifier") or aws_cdk.DefaultStackSynthesizer.DEFAULT_QUALIFIER
)
# List of required tags that every stack must have
required_tags = [
    {"Key": "Application", "Value": "VEW"},
    {"Key": "vew:cost-category", "Value": "shared"},
]

# Apply required tags to all resources in the app
# for tag in required_tags:
# aws_cdk.Tags.of(app).add(tag["Key"], tag["Value"])

base_config = config.BaseConfig(
    environment=environment,
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region"),
    web_app_account=app.node.try_get_context("account"),
    image_service_account=app.node.try_get_context("image-service-account"),
    catalog_service_account=app.node.try_get_context("catalog-service-account"),
    hosted_zone_id=app.node.try_get_context("hosted-zone-id"),
    hosted_zone_name=app.node.try_get_context("hosted-zone-name"),
)

if constants.PRIVATE_API_ENDPOINT:
    prerequisites_app_config = config.AppConfig(
        **base_config.dict(),
        component_name="prerequisites",
        environment_config=config.env_config[environment],
        component_specific=dict(),
    )

packaging_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="packaging",
    environment_config=config.env_config[environment],
    component_specific=config.packaging_app_config[environment],
)

projects_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="projects",
    environment_config=config.env_config[environment],
    component_specific=config.projects_app_config[environment],
)

publishing_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="publishing",
    environment_config=config.env_config[environment],
    component_specific=config.publishing_app_config[environment],
)

provisioning_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="provisioning",
    environment_config=config.env_config[environment],
    component_specific=config.provisioning_app_config[environment],
)

authorization_app_config = config.AppConfig(
    **base_config.dict(),
    component_name=constants.AUTH_BC_NAME,
    environment_config=config.env_config[environment],
    component_specific=config.authorization_app_config[environment],
)

image_key_app_config = config.AppConfig(
    account=base_config.image_service_account,
    web_app_account=base_config.web_app_account,
    component_name="image-key",
    component_specific=config.image_key_app_config[environment],
    environment=base_config.environment,
    environment_config=config.env_config[environment],
    region=app.node.try_get_context("image-service-region"),
)

image_sharing_app_config = config.AppConfig(
    account=base_config.image_service_account,
    web_app_account=base_config.web_app_account,
    component_name="image-sharing",
    component_specific=config.image_key_app_config[environment],
    environment=base_config.environment,
    environment_config=config.env_config[environment],
    region=app.node.try_get_context("image-service-region"),
)

product_packaging_app_config = config.AppConfig(
    account=base_config.image_service_account,
    web_app_account=base_config.web_app_account,
    component_name="product-packaging",
    component_specific=config.product_packaging_app_config[environment],
    environment=base_config.environment,
    environment_config=config.env_config[environment],
    region=app.node.try_get_context("image-service-region"),
)

product_publishing_app_config = config.AppConfig(
    account=base_config.catalog_service_account,
    web_app_account=base_config.web_app_account,
    region=app.node.try_get_context("catalog-service-region"),
    environment=base_config.environment,
    component_name="product-publishing",
    component_specific=config.product_publishing_app_config[environment],
    environment_config=config.env_config[environment],
)

oauth_app_config = config.AppConfig(
    **base_config.dict(),
    component_name="oauth",
    environment_config=config.env_config[environment],
    component_specific={},
)

if constants.PRIVATE_API_ENDPOINT:
    prerequisites_app_stack = prerequisites_app_stack.PrerequisitesAppStack(
        app,
        "PrerequisitesAppStack",
        app_config=prerequisites_app_config,
        stack_name=base_config.format_base_resource_name("prerequisites"),
        env=aws_cdk.Environment(
            account=prerequisites_app_config.account,
            region=prerequisites_app_config.region,
        ),
    )

shared_deployment_infrastructure_config = config.AppConfig(
    **base_config.dict(),
    component_name="dep-infra",
    environment_config=config.env_config[environment],
    component_specific=dict(),
)

shared_dep_stack = shared_deployment_infrastructure.SharedDeploymentInfrastructure(
    app,
    "SharedDeploymentInfrastructure",
    app_config=shared_deployment_infrastructure_config,
    stack_name=base_config.format_base_resource_name("shared-deployment-infrastructure"),
    env=aws_cdk.Environment(account=base_config.account, region=base_config.region),
)

projects_stack = projects_app_stack.ProjectsAppStack(
    app,
    "ProjectsAppStack",
    app_config=projects_app_config,
    stack_name=base_config.format_base_resource_name("projects"),
    env=aws_cdk.Environment(account=projects_app_config.account, region=projects_app_config.region),
    custom_api_domain=custom_domain if custom_domain else "",
    organization_id=organization_id,
    image_service_account_id=base_config.image_service_account,
    catalog_service_account_id=base_config.catalog_service_account,
    ci_commit_sha=ci_commit_sha,
    qualifier=qualifier,
    provision_private_endpoint=constants.PRIVATE_API_ENDPOINT,
    vpc_endpoint=(prerequisites_app_stack.vpc_endpoint if constants.PRIVATE_API_ENDPOINT else None),
)

if constants.PRIVATE_API_ENDPOINT:
    projects_stack.add_dependency(prerequisites_app_stack)

image_key_regional_stacks: list[image_key_app_stack.ImageKeyAppStack] = []
for region in image_key_app_config.environment_config["enabled-workbench-regions"]:
    image_key_regional_app_config = config.AppConfig(
        account=base_config.image_service_account,
        web_app_account=base_config.web_app_account,
        component_name="image-key",
        component_specific=config.image_key_app_config[environment],
        environment=base_config.environment,
        environment_config=config.env_config[environment],
        region=region,
    )
    image_key_regional_stacks.append(
        image_key_app_stack.ImageKeyAppStack(
            app,
            f"ImageKeyAppStack{image_key_regional_app_config.format_to_pascal_case(region)}",
            app_config=image_key_regional_app_config,
            env=aws_cdk.Environment(
                account=image_key_regional_app_config.account,
                region=image_key_regional_app_config.region,
            ),
            id_suffix=image_key_regional_app_config.format_to_pascal_case(region),
            organization_id=organization_id,
            stack_name=base_config.format_base_resource_name(f"image-key-{region}"),
        )
    )

image_sharing_stack = image_sharing_app_stack.ImageSharingAppStack(
    app,
    "ImageSharingAppStack",
    app_config=image_sharing_app_config,
    cross_region_references=True,
    env=aws_cdk.Environment(account=image_sharing_app_config.account, region=image_sharing_app_config.region),
    keys=[image_key_regional_stack.key.key for image_key_regional_stack in image_key_regional_stacks],
    regions=set(
        image_sharing_app_config.environment_config["enabled-workbench-regions"] + [image_sharing_app_config.region]
    ),
    stack_name=base_config.format_base_resource_name("image-sharing"),
    web_application_account=base_config.account,
)

product_packaging_stack = product_packaging_app_stack.ProductPackagingAppStack(
    app,
    "ProductPackagingAppStack",
    app_config=product_packaging_app_config,
    env=aws_cdk.Environment(
        account=product_packaging_app_config.account,
        region=product_packaging_app_config.region,
    ),
    stack_name=base_config.format_base_resource_name("product-packaging"),
    web_application_account=base_config.account,
)

packaging_stack = packaging_app_stack.PackagingAppStack(
    app,
    "PackagingAppStack",
    app_config=packaging_app_config,
    stack_name=base_config.format_base_resource_name("packaging"),
    env=aws_cdk.Environment(account=packaging_app_config.account, region=packaging_app_config.region),
    product_packaging_topic=product_packaging_stack.product_packaging_topic,
    custom_api_domain=custom_domain if custom_domain else "",
    provision_private_endpoint=constants.PRIVATE_API_ENDPOINT,
    vpc_endpoint=(prerequisites_app_stack.vpc_endpoint if constants.PRIVATE_API_ENDPOINT else None),
)

publishing_stack = publishing_app_stack.PublishingAppStack(
    app,
    "PublishingAppStack",
    app_config=publishing_app_config,
    stack_name=base_config.format_base_resource_name("publishing"),
    env=aws_cdk.Environment(account=publishing_app_config.account, region=publishing_app_config.region),
    lambda_exec_api_arns=[
        projects_stack.api.api.arn_for_execute_api(
            method="GET",
            path="/internal/projects",
            stage=projects_stack.api.api.deployment_stage.stage_name,
        ),
    ],
    custom_api_domain=custom_domain if custom_domain else "",
    provision_private_endpoint=constants.PRIVATE_API_ENDPOINT,
    vpc_endpoint=(prerequisites_app_stack.vpc_endpoint if constants.PRIVATE_API_ENDPOINT else None),
)

catalog_service_topics = []
for region in product_publishing_app_config.environment_config["enabled-workbench-regions"]:
    catalog_srv_regional_app_config = config.AppConfig(
        account=base_config.catalog_service_account,
        web_app_account=base_config.web_app_account,
        component_name="catalog-service-regional",
        component_specific=config.catalog_service_regional_app_config[environment],
        environment=base_config.environment,
        environment_config=config.env_config[environment],
        region=region,
    )
    catalog_srv_regional_stack = catalog_service_regional_stack.CatalogServiceRegionalStack(
        app,
        f"CatalogServiceRegionalStack{catalog_srv_regional_app_config.format_to_pascal_case(region)}",
        env=aws_cdk.Environment(
            account=catalog_srv_regional_app_config.account,
            region=catalog_srv_regional_app_config.region,
        ),
        cross_region_references=True,
        stack_name=base_config.format_base_resource_name(f"catalog-service-{region}"),
        app_config=catalog_srv_regional_app_config,
        organization_id=organization_id,
        web_app_account_id=base_config.account,
    )
    catalog_service_topics.append(catalog_srv_regional_stack.topic)

provisioning_stack = provisioning_app_stack.ProvisioningAppStack(
    app,
    "ProvisioningAppStack",
    app_config=provisioning_app_config,
    stack_name=base_config.format_base_resource_name("provisioning"),
    env=aws_cdk.Environment(account=provisioning_app_config.account, region=provisioning_app_config.region),
    lambda_exec_api_arns=[],
    catalog_service_topics=catalog_service_topics,
    organization_id=organization_id,
    custom_api_domain=custom_domain if custom_domain else "",
    provision_private_endpoint=constants.PRIVATE_API_ENDPOINT,
    vpc_endpoint=(prerequisites_app_stack.vpc_endpoint if constants.PRIVATE_API_ENDPOINT else None),
)

product_publishing_stack = product_publishing_app_stack.ProductPublishingAppStack(
    app,
    "ProductPublishingAppStack",
    app_config=product_publishing_app_config,
    env=aws_cdk.Environment(
        account=product_publishing_app_config.account,
        region=product_publishing_app_config.region,
    ),
    stack_name=base_config.format_base_resource_name("product-publishing"),
    image_service_account_id=base_config.image_service_account,
    web_app_account_id=base_config.account,
)

packaging_stack.add_dependency(projects_stack)
packaging_stack.add_dependency(publishing_stack)
provisioning_stack.add_dependency(projects_stack)
provisioning_stack.add_dependency(publishing_stack)
publishing_stack.add_dependency(projects_stack)

security_stack_config = config.AppConfig(
    **base_config.dict(),
    component_name="security",
    environment_config=config.env_config[environment],
    component_specific=dict(),
)

security_stack = security_stack.SecurityStack(
    app,
    "SecurityStack",
    app_config=security_stack_config,
    stack_name=base_config.format_base_resource_name("security"),
    env=aws_cdk.Environment(account=base_config.account, region=base_config.region),
    apis=[
        projects_stack.api,
    ],
)

api_integration_stack = None

if custom_domain and cert_arn:
    mappings = [
        integration_stack.ApiToPathMapping(api=api, base_path=base_path)
        for api, base_path in [
            (packaging_stack.api.api, constants.CUSTOM_DNS_API_PATH_PACKAGING),
            (projects_stack.api.api, constants.CUSTOM_DNS_API_PATH_PROJECTS),
            (projects_stack.api.iam_api, constants.CUSTOM_DNS_IAM_API_PATH_PROJECTS),
            (provisioning_stack.api.api, constants.CUSTOM_DNS_API_PATH_PROVISIONING),
            (
                provisioning_stack.api.iam_api,
                constants.CUSTOM_DNS_IAM_API_PATH_PROVISIONING,
            ),
            (publishing_stack.api.api, constants.CUSTOM_DNS_API_PATH_PUBLISHING),
            (projects_stack.s2s_api.api, constants.CUSTOM_DNS_S2S_API_PATH_PROJECTS),
            (
                provisioning_stack.s2s_api.api,
                constants.CUSTOM_DNS_S2S_API_PATH_PROVISIONING,
            ),
        ]
    ]

    api_integration_mapping = integration_stack.ApiIntegrationMapping(
        domain_name=f"{custom_domain}",
        cert_arn=cert_arn,
        mappings=mappings,
    )

    api_integration_config = config.AppConfig(
        **base_config.dict(),
        component_name="api-integration",
        environment_config=config.env_config[environment],
        component_specific=dict(),
    )

    api_integration_stack = integration_stack.ApiIntegrationStack(
        scope=app,
        id="ApiIntegrationStack",
        app_config=api_integration_config,
        api_integration_mapping=api_integration_mapping,
        env=aws_cdk.Environment(account=base_config.account, region=base_config.region),
        provision_private_endpoint=constants.PRIVATE_API_ENDPOINT,
        vpc_endpoint_ips=(prerequisites_app_stack.vpc_endpoint_ips if constants.PRIVATE_API_ENDPOINT else None),
    )
    api_integration_stack.add_dependency(packaging_stack)
    api_integration_stack.add_dependency(projects_stack)
    api_integration_stack.add_dependency(publishing_stack)
    api_integration_stack.add_dependency(provisioning_stack)


api_integration_permissions_stack = integration_permissions_stack.ApiIntegrationPermissionsStack(
    scope=app,
    id="ApiIntegrationPermissionsStack",
    stack_name=base_config.format_base_resource_name("api-integration-permissions"),
    env=aws_cdk.Environment(account=base_config.account, region=base_config.region),
)

api_integration_permissions_stack.add_dependency(packaging_stack)
api_integration_permissions_stack.add_dependency(projects_stack)
api_integration_permissions_stack.add_dependency(publishing_stack)
api_integration_permissions_stack.add_dependency(provisioning_stack)
if api_integration_stack:
    api_integration_permissions_stack.add_dependency(api_integration_stack)

oauth_integration_stack = integration_oauth_stack.IntegrationOauthStack(
    scope=app,
    id="OAuthIntegrationStack",
    app_config=oauth_app_config,
    stack_name=base_config.format_base_resource_name("oauth"),
    env=aws_cdk.Environment(
        account=base_config.account,
        region=oauth_app_config.environment_config["cognito-region"],
    ),
)

packaging_stack.add_dependency(shared_dep_stack)
projects_stack.add_dependency(shared_dep_stack)
provisioning_stack.add_dependency(shared_dep_stack)
publishing_stack.add_dependency(shared_dep_stack)

authorization_stack = authorization_app_stack.AuthorizationAppStack(
    app,
    "AuthorizationAppStack",
    authorization_app_config,
    stack_name=base_config.format_base_resource_name(constants.AUTH_BC_NAME),
    env=aws_cdk.Environment(account=authorization_app_config.account, region=authorization_app_config.region),
)

projects_stack.add_dependency(authorization_stack)

aws_cdk.Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(reports=True, verbose=True))
aws_cdk.Aspects.of(app).add(cdk_nag.NIST80053R4Checks(reports=True, verbose=True))
aws_cdk.Aspects.of(app).add(cdk_nag.NIST80053R5Checks(reports=True, verbose=True))
aws_cdk.Aspects.of(app).add(cdk_nag.PCIDSS321Checks(reports=True, verbose=True))

# Authorization Stack suppressions
cdk_nag.NagSuppressions.add_stack_suppressions(
    authorization_stack,
    suppressions=[
        cdk_nag.NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Auth lambda needs access to SSM parameters containing policy store IDs.",
        ),
    ],
    apply_to_nested_stacks=True,
)

# Projects Stack suppressions
cdk_nag.NagSuppressions.add_stack_suppressions(
    projects_stack,
    suppressions=[
        cdk_nag.NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Onboarding lambda requires permissions to read all account secrets, leading to wildcard",
        ),
    ],
    apply_to_nested_stacks=True,
)

# Provisioning Stack suppressions
cdk_nag.NagSuppressions.add_stack_suppressions(
    provisioning_stack,
    suppressions=[
        cdk_nag.NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Internal API features the path /internal/projects/<project_id>/products/provisioned, <project_id> leading to wildcard",
        ),
    ],
    apply_to_nested_stacks=True,
)

app.synth()
