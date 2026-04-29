import enum
import typing

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import (
    aws_apigateway,
    aws_dynamodb,
    aws_ec2,
    aws_events,
    aws_iam,
    aws_scheduler,
    aws_ssm,
)

from app.publishing import domain
from app.shared.api import bounded_contexts
from infra import config, constants
from infra.auth import publishing_auth, publishing_auth_schema
from infra.backend import vew_bounded_context_stack
from infra.constructs import (
    backend_app_api_auth,
    backend_app_entrypoints,
    backend_app_event_bus,
    backend_app_openapi,
    backend_app_storage,
    shared_layer,
)
from infra.constructs.ami_sharing import ami_sharing_state_machine
from infra.constructs.eventbridge import l3_event_bus
from infra.helpers import ops_monitoring

# Global variables
VEW_SERVICE = "Publishing"

PRODUCT_PUBLISHING_ADMIN_ROLE = constants.PRODUCT_PUBLISHING_ADMIN_ROLE
PRODUCT_PUBLISHING_USE_CASE_ROLE = constants.PRODUCT_PUBLISHING_USE_CASE_ROLE
PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE = constants.PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE
PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE = constants.PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE
PRODUCT_PUBLISHING_IMAGE_SERVICE_KEY_NAME = constants.IMAGE_SHARING_KEY_NAME
PRODUCT_PROVISIONING_ROLE = constants.PRODUCT_PROVISIONING_ROLE

WORKBENCH_PRODUCT_TEMPLATE_NAME = "templates/workbench-template.yml"
VIRTUAL_TARGET_TEMPLATE_NAME = "templates/virtual-target-template.yml"
CONTAINER_TEMPLATE_NAME = "templates/container-template.yml"
USED_AMI_LIST_FILE_PATH = "amis/used-ami-list.json"

TECHNICAL_PARAMETERS_NAMES = ["CpuArchitecture", "LaunchType", "OwnerTID"]

GSI_ATTRIBUTE_NAME_ENTITY = "entity"
GSI_NAME_ENTITIES = "gsi_entities"
GSI_NAME_CUSTOM_QUERY_BY_STATUS = "gsi_custom_query_by_status"
RESOURCE_UPDATE_CONSTRAINT_VALUE = "ALLOWED"


class Entrypoint(enum.StrEnum):
    API = "api"
    DOMAIN_EVENTS = "domain-events"
    PROJECTS_EVENTS = "projects-events"
    AMI_SHARING = "ami-sharing"
    PACKAGING_EVENTS = "packaging-events"
    PRODUCT_VERSION_SYNC_EVENTS = "product-version-sync-events"


class PublishingAppStack(vew_bounded_context_stack.VEWBoundedContextStack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        custom_api_domain: typing.Optional[str],
        provision_private_endpoint: bool = False,
        vpc_endpoint: aws_ec2.IVpcEndpoint | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, app_config=app_config, **kwargs)

        self._tools_account_id = None
        self._image_service_account_id = None

        self.configure_event_buses(app_config)

        audit_logging_key_arn = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "SharedSharedAuditLogKeyARN",
            constants.AUDIT_LOGGING_KEY_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value

        audit_logging_key_name = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "SharedSharedAuditLogKeyName",
            constants.AUDIT_LOGGING_KEY_NAME_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value

        product_version_limit_param = aws_ssm.StringParameter(
            self,
            "ProductVersionLimitParam",
            description="Number of product versions allowed for publishing of product.",
            parameter_name=f"/{app_config.format_resource_name('api')}/product-limit-version",
            string_value=str(app_config.component_specific["product-limit-version"]),
        )

        product_rc_version_limit_param = aws_ssm.StringParameter(
            self,
            "ProductReleaseCandidateVersionLimitParam",
            description="Number of product release candidate versions allowed for publishing of product.",
            parameter_name=f"/{app_config.format_resource_name('api')}/product-limit-rc-version",
            string_value=str(app_config.component_specific["product-limit-rc-version"]),
        )

        # EventBridge scheduler group
        self._scheduler_group = aws_scheduler.CfnScheduleGroup(
            self,
            "SchedulerGroup",
            name=f"{app_config.bounded_context_name}",
        )

        # DynamoDB
        self._storage = backend_app_storage.BackendAppStorage(
            self,
            "PublishingAppStorage",
            app_config,
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_ENTITIES,
            partition_key=aws_dynamodb.Attribute(
                name=GSI_ATTRIBUTE_NAME_ENTITY, type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_STATUS,
            partition_key=aws_dynamodb.Attribute(name="QPK_STATUS", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="QSK_IMAGE_TAG", type=aws_dynamodb.AttributeType.STRING),
        )

        # Lambda functions
        self._publishing_app_layer = shared_layer.SharedLayer(
            self,
            "PublishingAppLayer",
            layer_version_name="publishing_app_libraries",
            entry="app/publishing/libraries",
        )
        self._shared_app_layer = shared_layer.SharedLayer(
            self,
            "SharedAppLayer",
            layer_version_name="shared_app_libraries",
            entry="app/shared",
        )

        domain_event_handler_name = app_config.format_resource_name(Entrypoint.DOMAIN_EVENTS)
        projects_event_handler_name = app_config.format_resource_name(Entrypoint.PROJECTS_EVENTS)
        ami_sharing_handler_name = app_config.format_resource_name(Entrypoint.AMI_SHARING)
        packaging_event_handler_name = app_config.format_resource_name(Entrypoint.PACKAGING_EVENTS)
        self._product_sync_events = app_config.format_resource_name(Entrypoint.PRODUCT_VERSION_SYNC_EVENTS)

        self._backend_app = backend_app_entrypoints.BackendAppEntrypoints(
            self,
            "PublishingApp",
            app_config=app_config,
            global_env_vars={
                "POWERTOOLS_SERVICE_NAME": VEW_SERVICE,
            },
            app_entry_points=[
                backend_app_entrypoints.AppEntryPoint(
                    name=app_config.format_resource_name(Entrypoint.API),
                    app_root="app",
                    lambda_root="app/publishing",
                    entry="app/publishing/entrypoints/api",
                    environment={
                        "TABLE_NAME": self._storage.table.table_name,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "GSI_NAME_CUSTOM_QUERY_BY_STATUS": GSI_NAME_CUSTOM_QUERY_BY_STATUS,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "AUDIT_LOGGING_KEY_NAME": audit_logging_key_name,
                        "API_BASE_PATH": constants.CUSTOM_DNS_API_PATH_PUBLISHING,
                        "STRIP_PREFIXES": constants.CUSTOM_DNS_API_PATH_PUBLISHING,
                        "TOOLS_AWS_ACCOUNT_ID": self.get_tools_account_id(app_config),
                        "ADMIN_ROLE": PRODUCT_PUBLISHING_ADMIN_ROLE,
                        "PRODUCT_VERSION_LIMIT_PARAM_NAME": product_version_limit_param.parameter_name,
                        "PRODUCT_RC_VERSION_LIMIT_PARAM_NAME": product_rc_version_limit_param.parameter_name,
                        "CUSTOM_DNS": custom_api_domain,
                        "TEMPLATES_S3_BUCKET_NAME": app_config.component_specific["templates-s3-bucket-name"].format(
                            environment=app_config.environment,
                            tools_account_id=self.get_tools_account_id(app_config),
                            region=app_config.region,
                        ),
                        "WORKBENCH_TEMPLATE_FILE_PATH": WORKBENCH_PRODUCT_TEMPLATE_NAME,
                        "VIRTUAL_TARGET_TEMPLATE_FILE_PATH": VIRTUAL_TARGET_TEMPLATE_NAME,
                        "CONTAINER_TEMPLATE_NAME_FILE_PATH": CONTAINER_TEMPLATE_NAME,
                        "USED_AMI_LIST_FILE_PATH": USED_AMI_LIST_FILE_PATH,
                        "LAYER_VERSION": self._shared_app_layer.layer.layer_version_arn,
                    },
                    permissions=[
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "secretsmanager:GetSecretValue",
                                    "secretsmanager:DescribeSecret",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    audit_logging_key_arn,
                                ],
                            )
                        ),
                        lambda lambda_f: product_version_limit_param.grant_read(lambda_f),
                        lambda lambda_f: product_rc_version_limit_param.grant_read(lambda_f),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                    ],
                    reserved_concurrency=app_config.component_specific["api-lambda-reserved-concurrency"],
                    provisioned_concurrency=app_config.component_specific["api-lambda-provisioned-concurrency"],
                    timeout=aws_cdk.Duration.seconds(5),
                    memory_size=1792,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=domain_event_handler_name,
                    app_root="app",
                    lambda_root="app/publishing",
                    entry="app/publishing/entrypoints/domain_event_handler",
                    environment={
                        "TABLE_NAME": self._storage.table.table_name,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        # Only string values allowed - Converting to comma-separeted list
                        "TECHNICAL_PARAMETERS_NAMES": ",".join(TECHNICAL_PARAMETERS_NAMES),
                        "TOOLS_AWS_ACCOUNT_ID": self.get_tools_account_id(app_config),
                        "ADMIN_ROLE": PRODUCT_PUBLISHING_ADMIN_ROLE,
                        "USE_CASE_ROLE": PRODUCT_PUBLISHING_USE_CASE_ROLE,
                        "LAUNCH_CONSTRAINT_ROLE": PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE,
                        "TEMPLATES_S3_BUCKET_NAME": app_config.component_specific["templates-s3-bucket-name"].format(
                            environment=app_config.environment,
                            tools_account_id=self.get_tools_account_id(app_config),
                            region=app_config.region,
                        ),
                        "NOTIFICATION_CONSTRAINT_ARN": app_config.component_specific[
                            "notification-constraint-arn"
                        ].format(tools_account_id=self.get_tools_account_id(app_config)),
                        "WORKBENCH_TEMPLATE_FILE_PATH": WORKBENCH_PRODUCT_TEMPLATE_NAME,
                        "VIRTUAL_TARGET_TEMPLATE_FILE_PATH": VIRTUAL_TARGET_TEMPLATE_NAME,
                        "CONTAINER_TEMPLATE_NAME_FILE_PATH": CONTAINER_TEMPLATE_NAME,
                        "RESOURCE_UPDATE_CONSTRAINT_VALUE": RESOURCE_UPDATE_CONSTRAINT_VALUE,
                        "GSI_NAME_CUSTOM_QUERY_BY_STATUS": GSI_NAME_CUSTOM_QUERY_BY_STATUS,
                        "IMAGE_SERVICE_AWS_ACCOUNT_ID": self.get_image_service_account_id(app_config),
                        "USED_AMI_LIST_FILE_PATH": USED_AMI_LIST_FILE_PATH,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=None,
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=1792,
                    asynchronous=True,
                    cross_bc_api_access={
                        bounded_contexts.BoundedContext.PROJECTS: [
                            ("GET", "/internal/projects"),
                            ("GET", "/internal/accounts"),
                        ],
                    },
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=projects_event_handler_name,
                    app_root="app",
                    lambda_root="app/publishing",
                    entry="app/publishing/entrypoints/projects_event_handler",
                    environment={
                        "TABLE_NAME": self._storage.table.table_name,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "ADMIN_ROLE": PRODUCT_PUBLISHING_ADMIN_ROLE,
                        "USE_CASE_ROLE": PRODUCT_PUBLISHING_USE_CASE_ROLE,
                        "LAUNCH_CONSTRAINT_ROLE": PRODUCT_PUBLISHING_LAUNCH_CONSTRAINT_ROLE,
                        "PROVISIONING_ROLE": PRODUCT_PROVISIONING_ROLE,
                        # Only string values allowed - Converting to comma-separeted list
                        "TECHNICAL_PARAMETERS_NAMES": ",".join(TECHNICAL_PARAMETERS_NAMES),
                        "TOOLS_AWS_ACCOUNT_ID": self.get_tools_account_id(app_config),
                        "TEMPLATES_S3_BUCKET_NAME": app_config.component_specific["templates-s3-bucket-name"].format(
                            environment=app_config.environment,
                            tools_account_id=self.get_tools_account_id(app_config),
                            region=app_config.region,
                        ),
                        "NOTIFICATION_CONSTRAINT_ARN": app_config.component_specific[
                            "notification-constraint-arn"
                        ].format(tools_account_id=self.get_tools_account_id(app_config)),
                        "IMAGE_SERVICE_ROLE": PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE,
                        "IMAGE_SERVICE_AWS_ACCOUNT_ID": self.get_image_service_account_id(app_config),
                        "RESOURCE_UPDATE_CONSTRAINT_VALUE": RESOURCE_UPDATE_CONSTRAINT_VALUE,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_ADMIN_ROLE}",
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_USE_CASE_ROLE}",
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=None,
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=1792,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=ami_sharing_handler_name,
                    app_root="app",
                    lambda_root="app/publishing",
                    entry="app/publishing/entrypoints/ami_sharing",
                    environment={
                        "TABLE_NAME": self._storage.table.table_name,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "IMAGE_SERVICE_ROLE": PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE,
                        "IMAGE_SERVICE_AWS_ACCOUNT_ID": self.get_image_service_account_id(app_config),
                        "IMAGE_SERVICE_KEY_NAME": "-".join(
                            [
                                app_config.get_organization_prefix(),
                                app_config.get_application_prefix(),
                                PRODUCT_PUBLISHING_IMAGE_SERVICE_KEY_NAME,
                            ]
                        ),
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=None,
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=1792,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=packaging_event_handler_name,
                    app_root="app",
                    lambda_root="app/publishing",
                    entry="app/publishing/entrypoints/packaging_event_handler",
                    environment={
                        "TABLE_NAME": self._storage.table.table_name,
                        "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                        "TOOLS_AWS_ACCOUNT_ID": self.get_tools_account_id(app_config),
                        "ADMIN_ROLE": PRODUCT_PUBLISHING_ADMIN_ROLE,
                        "TEMPLATES_S3_BUCKET_NAME": app_config.component_specific["templates-s3-bucket-name"].format(
                            environment=app_config.environment,
                            tools_account_id=self.get_tools_account_id(app_config),
                            region=app_config.region,
                        ),
                        "WORKBENCH_TEMPLATE_FILE_PATH": WORKBENCH_PRODUCT_TEMPLATE_NAME,
                        "VIRTUAL_TARGET_TEMPLATE_FILE_PATH": VIRTUAL_TARGET_TEMPLATE_NAME,
                        "CONTAINER_TEMPLATE_NAME_FILE_PATH": CONTAINER_TEMPLATE_NAME,
                        "PRODUCT_VERSION_LIMIT_PARAM_NAME": product_version_limit_param.parameter_name,
                        "PRODUCT_RC_VERSION_LIMIT_PARAM_NAME": product_rc_version_limit_param.parameter_name,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: product_version_limit_param.grant_read(lambda_f),
                        lambda lambda_f: product_rc_version_limit_param.grant_read(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_ADMIN_ROLE}",
                                ],
                            )
                        ),
                    ],
                    reserved_concurrency=None,
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=256,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._product_sync_events,
                    app_root="app",
                    lambda_root="app/publishing",
                    entry="app/publishing/entrypoints/product_sync_event_handler",
                    environment={
                        "TABLE_NAME": self._storage.table.table_name,
                        "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PUBLISHING_IMAGE_SERVICE_ROLE}",
                                ],
                            )
                        ),
                    ],
                    reserved_concurrency=None,
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.minutes(6),
                    memory_size=1792,
                    asynchronous=True,
                    cross_bc_api_access={
                        bounded_contexts.BoundedContext.PROJECTS: [("GET", "/internal/projects")],
                    },
                ),
            ],
            app_layers=[
                self._publishing_app_layer.layer,
                self._shared_app_layer.layer,
            ],
        ).with_access_token_tag(app_config.environment_config.get("role-access-token", None))

        # API Gateway for UI client access
        api_acl_arn = None
        if not provision_private_endpoint:
            api_acl_arn = aws_ssm.StringParameter.from_string_parameter_attributes(
                self,
                "ui-waf-api-acl-arn",
                parameter_name=constants.WAF_API_ACL_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
            ).string_value

        self._open_api = backend_app_openapi.BackendAppOpenApi(
            self,
            "PublishingAppOpenApi",
            app_config,
            handler=self._backend_app.app_entries_function_aliases[app_config.format_resource_name(Entrypoint.API)],
            schema_directory="app/publishing/entrypoints/api/schema/",
            schema="proserve-workbench-publishing-api-schema.yaml",
            api_version="v1",
            version_description="First release of Publishing API",
            cache_enabled=False,
            waf_acl_arn=api_acl_arn,
            custom_domain=custom_api_domain,
            base_path=constants.CUSTOM_DNS_API_PATH_PUBLISHING,
            endpoint_type=(
                aws_apigateway.EndpointType.PRIVATE
                if provision_private_endpoint
                else aws_apigateway.EndpointType.REGIONAL
            ),
            vpc_endpoint=vpc_endpoint if provision_private_endpoint else None,
            cedar_policy_config=backend_app_api_auth.CedarPolicyConfig(
                cedar_schema=publishing_auth_schema.publishing_schema,
                cedar_policies=publishing_auth.publishing_bc_auth_policies,
            ),
        )

        # Ami sharing step function
        self._ami_sharing_state_machine = ami_sharing_state_machine.AmiSharingStateMachine(
            self,
            "AmiSharingStateMachine",
            app_config=app_config,
            ami_sharing_lambda=self._backend_app.app_entries_functions[ami_sharing_handler_name],
        )

        # Subscribe to domain events
        self._event_bus.l3_event_bus.subscribe_to_events(
            name="publishing-domain-events-rule",
            lambda_function=self._backend_app.app_entries_functions[domain_event_handler_name],
            events=[
                "ProductVersionAmiShared",
                "ProductVersionNameUpdated",
                "ProductArchivingStarted",
                "ProductVersionRetirementStarted",
                "ProductVersionPublished",
                "ProductVersionUnpublished",
                "ProductUnpublished",
                "ProductAvailabilityUpdated",
            ],
        )

        self._event_bus.l3_event_bus.subscribe_to_events(
            name="publishing-ami-sharing-event-rule",
            state_machine=self._ami_sharing_state_machine.state_machine,
            events=[
                "ProductVersionCreationStarted",
                "ProductVersionUpdateStarted",
                "ProductVersionPromotionStarted",
                "ProductVersionRetryStarted",
                "ProductVersionRestorationStarted",
            ],
        )

        # Subscribe to other Bounded Contexts
        projects_event_bus = l3_event_bus.from_bounded_context(
            self, "projects-bus", app_config=app_config, bounded_context_name="projects"
        )
        projects_event_bus.subscribe_to_events(
            name="projects-events-rule",
            lambda_function=self._backend_app.app_entries_functions[projects_event_handler_name],
            events=["ProjectAccountOnBoarded"],
        )

        packaging_event_bus = l3_event_bus.from_bounded_context(
            self,
            "packaging-bus",
            app_config=app_config,
            bounded_context_name="packaging",
        )
        packaging_event_bus.subscribe_to_events(
            name="packaging-events-rule",
            lambda_function=self._backend_app.app_entries_functions[packaging_event_handler_name],
            events=[
                "ImageRegistrationCompleted",
                "ImageDeregistered",
            ],
        )

        packaging_event_bus.subscribe_to_events(
            name="packaging-event-automated-image-rule",
            lambda_function=self._backend_app.app_entries_functions[packaging_event_handler_name],
            events=["AutomatedImageRegistrationCompleted"],
            event_detail_match={"productId": aws_events.Match.exists()},
        )

        # Stack based suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path="/PublishingAppStack/AmiSharingStateMachine/AmiSharingStateMachine/EventsRole/DefaultPolicy/Resource",
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R4-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="NIST.800.53.R5-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
                cdk_nag.NagPackSuppression(
                    id="PCI.DSS.321-IAMNoInlinePolicy",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
            ],
        )

        # --- Legacy export: kept for backward compatibility during migration. ---
        # --- Was consumed by integration_permissions_stack.py (now replaced by ServiceDiscoveryStack). ---
        # --- Safe to remove once the old CloudFormation stack is deleted. ---
        aws_cdk.CfnOutput(
            self,
            "PublishingApiInternalProductVersions",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/available-products/*/versions",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-product-versions",
        )
        aws_cdk.CfnOutput(
            self,
            "PublishingApiInternalAvailableProductVersion",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/available-products/*/versions/*",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-available-product-version",
        )
        aws_cdk.CfnOutput(
            self,
            "PublishingApiInternalProductVersion",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/products/*/versions/*",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-product-version",
        )

        aws_cdk.CfnOutput(
            self,
            "PublishingApiInternalPublishedAmis",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/published-amis",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-published-amis",
        )

        aws_cdk.CfnOutput(
            self,
            "PublishingProductSyncEventsHandlerName",
            value=self._backend_app.app_entries_functions[self._product_sync_events].role.role_arn,
            export_name=f"{app_config.component_name}-product-sync-events-handler-name",
        )
        # --- End legacy exports ---

        self.__configure_ops(app_config)

    def configure_event_buses(self, app_config):
        self._event_bus = backend_app_event_bus.BackendAppEventBus(
            self, "domain-event-bus", app_config, event_bus_name="domain-events"
        )

        self._infra_event_bus = backend_app_event_bus.BackendAppEventBus(
            self,
            "infrastructure-event-bus",
            app_config,
            event_bus_name=self.infra_event_bus_name(),
        )
        self.configure_image_integration_event_bus(app_config)

    def get_tools_account_id(self, app_config: config.AppConfig):
        tools_account_param_name = "tools-account-id-ssm-param"

        if not self._tools_account_id and app_config.environment_config[tools_account_param_name]:
            self._tools_account_id = aws_ssm.StringParameter.from_string_parameter_name(
                self,
                "tools_account",
                string_parameter_name=app_config.environment_config[tools_account_param_name].format(
                    environment=app_config.environment
                ),
            ).string_value

        return self._tools_account_id

    def get_image_service_account_id(self, app_config: config.AppConfig):
        image_service_account_param_name = "image-service-account-id-ssm-param"

        if not self._image_service_account_id and app_config.environment_config[image_service_account_param_name]:
            self._image_service_account_id = aws_ssm.StringParameter.from_string_parameter_name(
                self,
                "image_service_account",
                string_parameter_name=app_config.environment_config[image_service_account_param_name].format(
                    environment=app_config.environment
                ),
            ).string_value

        return self._image_service_account_id

    def configure_image_integration_event_bus(self, app_config: config.AppConfig):
        image_account_id = self.get_image_service_account_id(app_config)
        if image_account_id:
            self._infra_event_bus.allow_publish_from_account(image_account_id)

    def __configure_ops(self, app_config: config.AppConfig):
        (
            ops_monitoring.OpsMonitoringBuilder(
                self,
                app_config.format_resource_name("ops-dashboard"),
                constants.VEW_NAMESPACE,
                VEW_SERVICE,
                app_config,
            )
            .with_lambda_functions(self._backend_app.app_entries.values())
            .with_dynamodb_table(self._storage.table)
            .with_api_gateway(self._open_api.api)
            .with_step_functions([self._ami_sharing_state_machine.state_machine])
            .with_command_monitoring(domain_module=domain)
            .with_domain_event_monitoring(domain_module=domain)
            .build()
        )

    @property
    def backend_app(self) -> backend_app_entrypoints.BackendAppEntrypoints:
        return self._backend_app

    @property
    def internal_api(self) -> backend_app_openapi.BackendAppOpenApi | None:
        return self._open_api

    @property
    def table(self) -> aws_dynamodb.ITable | None:
        return self._storage.table

    @property
    def api(self) -> backend_app_openapi.BackendAppOpenApi:
        return self._open_api

    @property
    def publishing_table(self) -> backend_app_storage.BackendAppStorage:
        return self._storage

    @property
    def publishing_table_name(self) -> str:
        return self._storage.table_name

    @property
    def publishing_table_arn(self) -> str:
        return self._storage.table_arn

    @property
    def publishing_entry(self) -> backend_app_entrypoints.BackendAppEntrypoints:
        return self._backend_app

    @staticmethod
    def infra_event_bus_name() -> str:
        return "infrastructure-events"
