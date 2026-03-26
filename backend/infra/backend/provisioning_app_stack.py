import json
import typing

import aws_cdk
import cdk_nag
import constructs
from aws_cdk import (
    aws_apigateway,
    aws_dynamodb,
    aws_ec2,
    aws_events,
    aws_events_targets,
    aws_iam,
    aws_logs,
    aws_pipes_alpha,
    aws_scheduler,
    aws_sns,
    aws_ssm,
)

from app.provisioning import domain
from app.provisioning.domain.commands.provisioned_product_state import (
    sync_provisioned_product_state_command,
)
from app.provisioning.domain.events.provisioned_product_sync import (
    provisioned_product_status_out_of_sync,
)
from infra import config, constants
from infra.auth import provisioning_auth, provisioning_auth_schema
from infra.constructs import (
    backend_app_api_auth,
    backend_app_entrypoints,
    backend_app_event_bus,
    backend_app_openapi,
    backend_app_openapi_oauth,
    backend_app_storage,
    shared_layer,
)
from infra.constructs.eventbridge import l3_event_bus
from infra.constructs.pipes import topic_to_event_bus_pipe
from infra.constructs.provisioned_product_configuration import (
    provisioned_product_configuration_state_machine,
)
from infra.helpers import ops_monitoring

# Global variables
VEW_NAMESPACE = "VirtualEngineeringWorkbench"
VEW_SERVICE = "Provisioning"
GSI_ATTRIBUTE_NAME_ENTITY = "entity"
GSI_NAME_ENTITIES = "gsi_entities"
GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY = "gsi_custom_query_by_alternative_key"
GSI_NAME_CUSTOM_QUERY_BY_USER_KEY = "gsi_custom_query_by_user_key"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2 = "gsi_custom_query_by_alternative_key_2"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3 = "gsi_custom_query_by_alternative_keys_3"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4 = "gsi_custom_query_by_alternative_keys_4"
GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5 = "gsi_custom_query_by_alternative_keys_5"
PRODUCT_PROVISIONING_ROLE = constants.PRODUCT_PROVISIONING_ROLE
DEFAULT_PAGE_SIZE = "100"


class ProvisioningAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        custom_api_domain: typing.Optional[str],
        lambda_exec_api_arns: list[str],
        catalog_service_topics: list[aws_sns.ITopic],
        organization_id: str,
        provision_private_endpoint: bool = False,
        vpc_endpoint: aws_ec2.IVpcEndpoint | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        self._tools_account_id = None
        self.configure_event_buses(app_config, catalog_service_topics, organization_id)

        audit_logging_key_arn = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "SharedAuditLoggingKeyARN",
            constants.AUDIT_LOGGING_KEY_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value

        audit_logging_key_name = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "SharedAuditLoggingKeyName",
            constants.AUDIT_LOGGING_KEY_NAME_SSM_PARAM_NAME.format(environment=app_config.environment),
        ).string_value

        # Enabled workbench regions parameter
        enabled_workbench_regions_param = aws_ssm.StringListParameter(
            self,
            "EnabledWorkbenchRegionsParam",
            description="Enabled workbench regions.",
            parameter_name=f"/{app_config.format_resource_name('api')}/enabled-workbench-regions",
            string_list_value=list(app_config.environment_config["enabled-workbench-regions"]),
        )

        # Feature toggles parameter
        feature_toggles_param = aws_ssm.StringParameter(
            self,
            "FeatureTogglesParam",
            description="Feature toggles.",
            parameter_name=f"/{app_config.format_resource_name('api')}/feature-toggles",
            string_value="[]",
            tier=aws_ssm.ParameterTier.ADVANCED,
        )

        # Application version parameter
        application_version_param = aws_ssm.StringParameter(
            self,
            "ApplicationVersionParam",
            description="VEW Application Version",
            parameter_name=f"/{app_config.format_resource_name('api')}/application-version",
            string_value="3.12",
        )

        application_version_backend_param = aws_ssm.StringParameter(
            self,
            "ApplicationVersionBackendParam",
            description="VEW UI Application Version(Backend)",
            parameter_name=f"/{app_config.format_resource_name('api')}/application_version_backend",
            string_value="2.0",
        )

        application_version_frontend_param = aws_ssm.StringParameter(
            self,
            "ApplicationVersionFrontendParam",
            description="VEW UI Application Version(Frontend)",
            parameter_name=f"/{app_config.format_resource_name('api')}/application_version_frontend",
            string_value="2.0",
        )

        # Available networks parameter
        available_networks_param = aws_ssm.StringParameter(
            self,
            "AvailableNetworksParam",
            description="Available networks",
            parameter_name=f"/{app_config.format_resource_name('api')}/available-networks",
            string_value=json.dumps(app_config.component_specific["available-networks"]),
        )

        # Experimental provisioning per product limit
        experimental_provisioned_product_per_project_limit_param = aws_ssm.StringParameter(
            self,
            "experimental-provisioned-product-per-project-limit",
            description="Experimental provisioned product per project limit",
            parameter_name=f"/{app_config.format_resource_name('shared')}/experimental-provisioned-product-per-project-limit",
            string_value=json.dumps(
                app_config.component_specific["experimental-provisioned-product-per-project-limit"]
            ),
        )

        # Post provisioning document mapping
        provisioned_product_configuration_document_mapping_param = aws_ssm.StringParameter(
            self,
            "ProvisionedProductConfigurationDocumentMapping",
            description="Provisioned product configuration document mapping",
            parameter_name=f"/{app_config.format_resource_name('shared')}/provisioned-product-configuration-document-mapping",
            string_value=json.dumps(
                app_config.component_specific["provisioned-product-configuration-document-mapping"]
            ),
        )

        # Read projects api url
        projects_api_url = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "ProjectsApiUrl",
            f"/{app_config.format_resource_name_with_component('projects', 'api')}/api/url",
        ).string_value

        # Read publishing api url
        publishing_api_url = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "Publishing",
            f"/{app_config.format_resource_name_with_component('publishing', 'api')}/api/url",
        ).string_value

        # EventBridge scheduler group
        self._scheduler_group = aws_scheduler.CfnScheduleGroup(
            self,
            "SchedulerGroup",
            name=f"{app_config.bounded_context_name}",
        )

        # DynamoDB
        self._storage = backend_app_storage.BackendAppStorage(
            self,
            "ProvisioningAppStorage",
            app_config,
            enable_streaming=True,
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_ENTITIES,
            partition_key=aws_dynamodb.Attribute(
                name=GSI_ATTRIBUTE_NAME_ENTITY, type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_INVERTED_PK,
            partition_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="PK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY,
            partition_key=aws_dynamodb.Attribute(name="QPK_1", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_USER_KEY,
            partition_key=aws_dynamodb.Attribute(name="GSI_PK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="GSI_SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2,
            partition_key=aws_dynamodb.Attribute(name="QPK_2", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3,
            partition_key=aws_dynamodb.Attribute(name="QPK_3", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="QSK_3", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4,
            partition_key=aws_dynamodb.Attribute(name="PK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="QSK_3", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5,
            partition_key=aws_dynamodb.Attribute(name="QPK_4", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
        )

        # Lambda functions
        self._provisioning_app_layer = shared_layer.SharedLayer(
            self,
            "ProvisioningAppLayer",
            layer_version_name="provisioning_app_libraries",
            entry="app/provisioning/libraries",
        )
        self._shared_app_layer = shared_layer.SharedLayer(
            self,
            "SharedAppLayer",
            layer_version_name="shared_app_libraries",
            entry="app/shared",
        )

        # IAM role for scheduler
        scheduler_managed_policy = aws_iam.ManagedPolicy(
            self,
            "scheduler-policy",
            managed_policy_name="VEWWebProvisioningSchedulerRolePolicy",
            description="Grants permissions to publish events to event bus",
            statements=[
                aws_iam.PolicyStatement(
                    actions=["events:PutEvents"],
                    effect=aws_iam.Effect.ALLOW,
                    resources=[self._event_bus.event_bus_arn],
                )
            ],
        )

        scheduler_role = aws_iam.Role(
            self,
            "SchedulerIamRole",
            role_name=app_config.format_resource_name("scheduler-role"),
            assumed_by=aws_iam.ServicePrincipal("scheduler.amazonaws.com"),
            managed_policies=[scheduler_managed_policy],
        )

        log_level = "DEBUG" if app_config.environment in ["dev", "qa"] else "INFO"

        self._api_event_handler_name = app_config.format_resource_name("api")
        self._s2s_api_event_handler_name = app_config.format_resource_name("s2s-api")
        self._publishing_event_handler_name = app_config.format_resource_name("publishing-events")
        self._pp_evt_handler_name = app_config.format_resource_name("pp-events")
        self._pp_state_events_evt_handler_name = app_config.format_resource_name("pp-state-events")
        self._projects_events_handler_name = app_config.format_resource_name("projects-events")
        self._domain_events_handler_name = app_config.format_resource_name("domain-events")
        self._scheduled_jobs_handler_name = app_config.format_resource_name("scheduled-jobs")
        self._pp_configuration_evt_handler_name = app_config.format_resource_name("pp-configuration-events")
        common_env_vars_ddb = {
            "TABLE_NAME": self._storage.table.table_name,
            "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
            "GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY,
            "GSI_NAME_CUSTOM_QUERY_BY_USER_KEY": GSI_NAME_CUSTOM_QUERY_BY_USER_KEY,
            "GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEY_2,
            "GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_3,
            "GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_4,
            "GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5": GSI_NAME_CUSTOM_QUERY_BY_ALT_KEYS_5,
            "POWERTOOLS_METRICS_NAMESPACE": VEW_NAMESPACE,
            "POWERTOOLS_SERVICE_NAME": VEW_SERVICE,
            "LOG_LEVEL": log_level,
            "SPOKE_ACCOUNT_VPC_ID_PARAM_NAME": app_config.environment_config["spoke-account-vpc-id-param-name"],
            "PROVISIONING_SUBNET_SELECTOR": app_config.component_specific.get("provisioning-subnet-selector"),
            "PROVISIONING_SUBNET_SELECTOR_TAG": app_config.component_specific.get("provisioning-subnet-selector-tag"),
            "AUTHORIZE_USER_IP_ADDRESS_PARAM_VALUE": str(
                app_config.component_specific["authorize-user-ip-address-param-value"]
            ),
            "BOUNDED_CONTEXT": app_config.bounded_context_name,
            "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
            "PRODUCT_PROVISIONING_ROLE": PRODUCT_PROVISIONING_ROLE,
        }

        self._backend_app = backend_app_entrypoints.BackendAppEntrypoints(
            self,
            "ProvisioningApp",
            app_entry_points=[
                backend_app_entrypoints.AppEntryPoint(
                    name=self._api_event_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/api",
                    environment={
                        **common_env_vars_ddb,
                        "AUDIT_LOGGING_KEY_NAME": audit_logging_key_name,
                        "API_BASE_PATH": constants.CUSTOM_DNS_API_PATH_PROVISIONING,
                        "STRIP_PREFIXES": f"{constants.CUSTOM_DNS_API_PATH_PROVISIONING},{constants.CUSTOM_DNS_IAM_API_PATH_PROVISIONING}",
                        "DEFAULT_PAGE_SIZE": DEFAULT_PAGE_SIZE,
                        "ENABLED_WORKBENCH_REGIONS_PARAMETER_NAME": enabled_workbench_regions_param.parameter_name,
                        "FEATURE_TOGGLES_PARAM_NAME": feature_toggles_param.parameter_name,
                        "APPLICATION_VERSION_PARAMETER_NAME": application_version_param.parameter_name,
                        "AVAILABLE_NETWORKS_SSM_PARAMETER_NAME": available_networks_param.parameter_name,
                        "APPLICATION_VERSION_FRONTEND_PARAMETER_NAME": application_version_frontend_param.parameter_name,
                        "APPLICATION_VERSION_BACKEND_PARAMETER_NAME": application_version_backend_param.parameter_name,
                        "CUSTOM_DNS": custom_api_domain,
                        "FEATURE_SAAS_WORKBENCH": "true",
                        "EXPERIMENTAL_PROVISIONED_PRODUCT_PER_PROJECT_LIMIT_PARAMETER_NAME": experimental_provisioned_product_per_project_limit_param.parameter_name,
                        "PROJECTS_API_URL": projects_api_url,
                        "PUBLISHING_API_URL": publishing_api_url,
                        "LAMBDA_IAM_ROLE": f"{scheduler_role.role_arn}",
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
                                    f"arn:aws:iam::*:role/{PRODUCT_PROVISIONING_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: enabled_workbench_regions_param.grant_read(lambda_f),
                        lambda lambda_f: feature_toggles_param.grant_read(lambda_f),
                        lambda lambda_f: feature_toggles_param.grant_write(lambda_f),
                        lambda lambda_f: application_version_param.grant_read(lambda_f),
                        lambda lambda_f: available_networks_param.grant_read(lambda_f),
                        lambda lambda_f: application_version_frontend_param.grant_read(lambda_f),
                        lambda lambda_f: application_version_backend_param.grant_read(lambda_f),
                        lambda lambda_f: experimental_provisioned_product_per_project_limit_param.grant_read(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=["cloudwatch:GetMetricData"],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    "*",
                                ],
                            )
                        ),
                        lambda lambda_f: (
                            lambda_f.add_to_role_policy(
                                statement=(
                                    (
                                        (
                                            aws_iam.PolicyStatement(
                                                actions=["execute-api:Invoke"],
                                                effect=aws_iam.Effect.ALLOW,
                                                resources=lambda_exec_api_arns,
                                            )
                                        )
                                    )
                                )
                            )
                            if lambda_exec_api_arns
                            else None
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "scheduler:GetSchedule",
                                    "scheduler:CreateSchedule",
                                    "scheduler:UpdateSchedule",
                                    "scheduler:DeleteSchedule",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:scheduler:{app_config.region}:{app_config.account}:schedule/{app_config.bounded_context_name}/*"
                                ],
                            )
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            aws_iam.PolicyStatement(
                                actions=["iam:PassRole"],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[scheduler_role.role_arn],
                                conditions={"StringLike": {"iam:PassedToService": "scheduler.amazonaws.com"}},
                            )
                        ),
                    ],
                    reserved_concurrency=app_config.component_specific["api-lambda-reserved-concurrency"],
                    provisioned_concurrency=app_config.component_specific["api-lambda-provisioned-concurrency"],
                    timeout=aws_cdk.Duration.seconds(10),
                    memory_size=1792,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._s2s_api_event_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/s2s_api",
                    environment={
                        **common_env_vars_ddb,
                        "AUDIT_LOGGING_KEY_NAME": audit_logging_key_name,
                        "API_BASE_PATH": constants.CUSTOM_DNS_S2S_API_PATH_PROVISIONING,
                        "STRIP_PREFIXES": constants.CUSTOM_DNS_S2S_API_PATH_PROVISIONING,
                        "DEFAULT_PAGE_SIZE": DEFAULT_PAGE_SIZE,
                        "AVAILABLE_NETWORKS_SSM_PARAMETER_NAME": available_networks_param.parameter_name,
                        "CUSTOM_DNS": custom_api_domain,
                        "EXPERIMENTAL_PROVISIONED_PRODUCT_PER_PROJECT_LIMIT_PARAMETER_NAME": experimental_provisioned_product_per_project_limit_param.parameter_name,
                        "PROJECTS_API_URL": projects_api_url,
                        "PUBLISHING_API_URL": publishing_api_url,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: experimental_provisioned_product_per_project_limit_param.grant_read(lambda_f),
                        lambda lambda_f: available_networks_param.grant_read(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["api-lambda-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(10),
                    memory_size=1792,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._publishing_event_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/publishing_event_handler",
                    environment={
                        **common_env_vars_ddb,
                        "AUDIT_LOGGING_KEY_NAME": audit_logging_key_name,
                        "PUBLISHING_API_URL": publishing_api_url,
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
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["publishing-events-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=256,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._domain_events_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/domain_event_handler",
                    environment={
                        **common_env_vars_ddb,
                        "PUBLISHING_API_URL": publishing_api_url,
                        "LAMBDA_IAM_ROLE": f"{scheduler_role.role_arn}",
                    },
                    permissions=[
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PROVISIONING_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "scheduler:GetSchedule",
                                    "scheduler:CreateSchedule",
                                    "scheduler:UpdateSchedule",
                                    "scheduler:DeleteSchedule",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:scheduler:{app_config.region}:{app_config.account}:schedule/{app_config.bounded_context_name}/*"
                                ],
                            )
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            aws_iam.PolicyStatement(
                                actions=["iam:PassRole"],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[scheduler_role.role_arn],
                                conditions={"StringLike": {"iam:PassedToService": "scheduler.amazonaws.com"}},
                            )
                        ),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["domain-event-lambda-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(60),
                    memory_size=1792,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._pp_evt_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/provisioned_product_event_handlers",
                    environment={
                        **common_env_vars_ddb,
                        "PUBLISHING_API_URL": publishing_api_url,
                    },
                    permissions=[
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PROVISIONING_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific[
                        "provisioning-events-lambda-reserved-concurrency"
                    ],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(15),
                    memory_size=1792,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._pp_state_events_evt_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/provisioned_product_state_event_handler",
                    environment={
                        **common_env_vars_ddb,
                        "PUBLISHING_API_URL": publishing_api_url,
                    },
                    permissions=[
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PROVISIONING_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["pp-state-events-lambda-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(60),
                    memory_size=256,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._projects_events_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/projects_event_handler",
                    environment={
                        **common_env_vars_ddb,
                        "PROJECTS_API_URL": projects_api_url,
                        "AVAILABLE_NETWORKS_SSM_PARAMETER_NAME": available_networks_param.parameter_name,
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: available_networks_param.grant_read(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["projects-events-lambda-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=256,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._scheduled_jobs_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/scheduled_jobs_handler",
                    environment={
                        **common_env_vars_ddb,
                        "PROJECTS_API_URL": projects_api_url,
                        "AVAILABLE_NETWORKS_SSM_PARAMETER_NAME": available_networks_param.parameter_name,
                        "PROVISIONED_PRODUCT_CLEANUP_CONFIG": json.dumps(
                            app_config.component_specific["pp-cleanup-config"]
                        ),
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
                                    f"arn:aws:iam::*:role/{PRODUCT_PROVISIONING_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: available_networks_param.grant_read(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["scheduled-jobs-lambda-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.minutes(7),
                    memory_size=1792,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=self._pp_configuration_evt_handler_name,
                    app_root="app",
                    lambda_root="app/provisioning",
                    entry="app/provisioning/entrypoints/provisioned_product_configuration_event_handler",
                    environment={
                        **common_env_vars_ddb,
                        "PROVISIONED_PRODUCT_CONFIGURATION_DOCUMENT_MAPPING_PARAM_NAME": provisioned_product_configuration_document_mapping_param.parameter_name,
                    },
                    permissions=[
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "sts:AssumeRole",
                                    "sts:TagSession",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:iam::*:role/{PRODUCT_PROVISIONING_ROLE}",
                                ],
                            )
                        ),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                        lambda lambda_f: provisioned_product_configuration_document_mapping_param.grant_read(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific[
                        "pp-configuration-events-lambda-reserved-concurrency"
                    ],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(10),
                    memory_size=256,
                ),
            ],
            app_layers=[
                self._provisioning_app_layer.layer,
                self._shared_app_layer.layer,
            ],
        ).with_access_token_tag(app_config.environment_config.get("role-access-token", None))

        # API Gateway for UI client access
        api_acl_arn = None
        if not provision_private_endpoint:
            api_acl_arn = aws_ssm.StringParameter.from_string_parameter_attributes(
                self,
                "ui-api-acl-arn",
                parameter_name=constants.WAF_API_ACL_ARN_SSM_PARAM_NAME.format(environment=app_config.environment),
            ).string_value

        self._open_api = backend_app_openapi.BackendAppOpenApi(
            self,
            "ProvisioningAppOpenApi",
            app_config,
            handler=self._backend_app.app_entries_function_aliases[app_config.format_resource_name("api")],
            schema_directory="app/provisioning/entrypoints/api/schema/",
            schema="proserve-workbench-provisioning-api-schema.yaml",
            api_version="v1",
            version_description="First release of Provisioning API",
            cache_enabled=False,
            waf_acl_arn=api_acl_arn,
            custom_domain=custom_api_domain,
            base_path=constants.CUSTOM_DNS_API_PATH_PROVISIONING,
            endpoint_type=(
                aws_apigateway.EndpointType.PRIVATE
                if provision_private_endpoint
                else aws_apigateway.EndpointType.REGIONAL
            ),
            vpc_endpoint=vpc_endpoint if provision_private_endpoint else None,
            cedar_policy_config=backend_app_api_auth.CedarPolicyConfig(
                cedar_schema=provisioning_auth_schema.provisioning_schema,
                cedar_policies=provisioning_auth.provisioning_bc_auth_policies,
            ),
            provision_iam_api=True,
            iam_role_access=config.VEWRole.PLATFORM_USER,
        )

        user_pool_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-userpool-id-ssm-param"].format(environment=app_config.environment),
        )

        self._s2s_open_api = backend_app_openapi_oauth.BackendAppOpenApiOauth(
            self,
            "ServiceIntegrationProvisioningOpenApi",
            app_config,
            handler=self._backend_app.app_entries_function_aliases[app_config.format_resource_name("s2s-api")],
            schema_directory="app/provisioning/entrypoints/s2s_api/schema/",
            schema="proserve-workbench-s2s-provisioning-api-schema.yaml",
            api_version="v1",
            version_description="First release of service to service Provisioning API",
            user_pool_id=user_pool_id,
            cache_enabled=False,
            waf_acl_arn=api_acl_arn if not provision_private_endpoint else None,
            endpoint_type=(
                aws_apigateway.EndpointType.PRIVATE
                if provision_private_endpoint
                else aws_apigateway.EndpointType.REGIONAL
            ),
            vpc_endpoint=vpc_endpoint if provision_private_endpoint else None,
        )

        # Provisioning product configuration step function
        self._provisioned_product_configuration_state_machine = (
            provisioned_product_configuration_state_machine.ProvisionedProductConfigurationStateMachine(
                self,
                "ProvisionedProductConfigurationStateMachine",
                app_config=app_config,
                provisioned_product_configuration_lambda=self._backend_app.app_entries_functions[
                    self._pp_configuration_evt_handler_name
                ],
            )
        )

        # Subscribe to domain events
        self._event_bus.l3_event_bus.subscribe_to_events(
            name="provisioning-domain-events-rule",
            lambda_function=self._backend_app.app_entries_functions[self._domain_events_handler_name],
            events=[
                "IdleProvisionedProductDetected",
                "ProductLaunchStarted",
                "ProvisionedProductRemovalStarted",
                "ProvisionedProductStartInitiated",
                "ProvisionedProductStopInitiated",
                "ProvisionedProductStatusOutOfSync",
                "ProvisionedProductStoppedForUpgrade",
                "ProvisionedProductStopForUpgradeFailed",
                "ProvisionedProductUpdateInitialized",
                "InsufficientCapacityReached",
                "ProvisionedProductStopped",
                "ProvisionedProductStoppedForUpdate",
                "ProvisionedProductUpgraded",
                "ProvisionedProductMarkedForAutoUpgrade",
                "ProvisionedProductAutoUpgradeTimedOut",
                "ProvisionedProductAutoUpgradeStarted",
                "ProvisionedProductRemovalRetried",
                "ProvisionedProductAutoStopDisableExpired",
            ],
        )

        self._event_bus.l3_event_bus.subscribe_to_events(
            name="pp-configuration-event-rule",
            state_machine=self._provisioned_product_configuration_state_machine.state_machine,
            events=[
                "ProvisionedProductConfigurationRequested",
            ],
        )

        # Subscribe to other Publishing BC
        publishing_event_bus = l3_event_bus.from_bounded_context(
            self,
            "publishing-bus",
            app_config=app_config,
            bounded_context_name="publishing",
        )

        publishing_event_bus.subscribe_to_events(
            name="publishing-events-rule",
            lambda_function=self._backend_app.app_entries_functions[self._publishing_event_handler_name],
            events=[
                "ProductAvailabilityUpdated",
                "ProductVersionPublished",
                "ProductVersionUnpublished",
                "RecommendedVersionSet",
            ],
        )

        # Subscribe to Projects BC
        projects_event_bus = l3_event_bus.from_bounded_context(
            self, "projects-bus", app_config=app_config, bounded_context_name="projects"
        )
        projects_event_bus.subscribe_to_events(
            name="projects-events-rule",
            lambda_function=self._backend_app.app_entries_functions[self._projects_events_handler_name],
            events=["UserUnAssigned"],
        )

        self.subscribe_to_external_events(app_config)

        # Metrics scheduler
        aws_events.Rule(
            self,
            "metrics-scheduler-rule",
            schedule=aws_events.Schedule.cron(minute="*/5"),  # every 5 mins
            targets=[
                aws_events_targets.LambdaFunction(
                    self._backend_app.app_entries_functions[self._scheduled_jobs_handler_name],
                    event=aws_events.RuleTargetInput.from_object({"jobName": "MetricProducerJob"}),
                )
            ],
            rule_name=app_config.format_resource_name("scheduled-metric-producer"),
        )

        aws_events.Rule(
            self,
            "sync-scheduler-rule",
            schedule=aws_events.Schedule.cron(minute="30"),  # once every hour at half hour to prevent overlap
            targets=[
                aws_events_targets.LambdaFunction(
                    self._backend_app.app_entries_functions[self._scheduled_jobs_handler_name],
                    event=aws_events.RuleTargetInput.from_object({"jobName": "ProvisionedProductSyncJob"}),
                )
            ],
            rule_name=app_config.format_resource_name("sync-job"),
        )

        # Cleanup: delete provisioned products when instances are dormant/abandoned, other schedulled cleanup
        aws_events.Rule(
            self,
            "cleanup-scheduler-rule",
            schedule=aws_events.Schedule.cron(minute="0", hour="20"),  # daily at 20:00 GMT
            targets=[
                aws_events_targets.LambdaFunction(
                    self._backend_app.app_entries_functions[self._scheduled_jobs_handler_name],
                    event=aws_events.RuleTargetInput.from_object({"jobName": "ProvisionedProductCleanupJob"}),
                )
            ],
            rule_name=app_config.format_resource_name("scheduled-cleanup"),
        )

        # Batch stop for provisioned products on weekends, 8AM UTC
        aws_events.Rule(
            self,
            "pp-batch-stop-scheduler-rule",
            schedule=aws_events.Schedule.cron(minute="0", hour="8", week_day="SAT,SUN"),  # Weekends 8AM UTC
            targets=[
                aws_events_targets.LambdaFunction(
                    self._backend_app.app_entries_functions[self._scheduled_jobs_handler_name],
                    event=aws_events.RuleTargetInput.from_object({"jobName": "ProvisionedProductBatchStopJob"}),
                )
            ],
            rule_name=app_config.format_resource_name("pp-batch-stop"),
        )

        # Add CloudFormation outputs for event handler names
        aws_cdk.CfnOutput(
            self,
            "ProvisioningApiEventHandlerName",
            value=self._backend_app.app_entries_functions[self._api_event_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-api-event-handler-name",
        )
        aws_cdk.CfnOutput(
            self,
            "ProvisioningS2SApiEventHandlerName",
            value=self._backend_app.app_entries_functions[self._s2s_api_event_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-s2s-api-event-handler-name",
        )
        aws_cdk.CfnOutput(
            self,
            "ProvisioningScheduledJobsHandlerName",
            value=self._backend_app.app_entries_functions[self._scheduled_jobs_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-scheduled-jobs-handler-name",
        )
        aws_cdk.CfnOutput(
            self,
            "ProvisioningProjectsEventsHandlerName",
            value=self._backend_app.app_entries_functions[self._projects_events_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-projects-events-handler-name",
        )
        aws_cdk.CfnOutput(
            self,
            "ProvisioningPublishingEventsHandlerName",
            value=self._backend_app.app_entries_functions[self._publishing_event_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-publishing-events-handler-name",
        )
        aws_cdk.CfnOutput(
            self,
            "ProvisioningDomainEventsHandlerName",
            value=self._backend_app.app_entries_functions[self._domain_events_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-domain-events-handler-name",
        )
        aws_cdk.CfnOutput(
            self,
            "ProvisioningProvisionedProductEventsHandlerName",
            value=self._backend_app.app_entries_functions[self._pp_evt_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-provisioned-product-events-handler-name",
        )
        aws_cdk.CfnOutput(
            self,
            "ProvisioningProvisionedProductStateEventsHandlerName",
            value=self._backend_app.app_entries_functions[self._pp_state_events_evt_handler_name].role.role_arn,
            export_name=f"{app_config.component_name}-provisioned-product-state-events-handler-name",
        )

        # Add Cloudformation outputs for internal available APIs
        aws_cdk.CfnOutput(
            self,
            "ProvisioningApiInternalProductsProvisioned",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/projects/*/products/provisioned/*",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-products-provisioned",
        )

        aws_cdk.CfnOutput(
            self,
            "ProvisioningApiInternalProvisionProducts",
            value=self._open_api.api.arn_for_execute_api(
                method="POST",
                path="/internal/projects/*/products/provisioned",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-provision-products",
        )

        aws_cdk.CfnOutput(
            self,
            "ProvisioningApiInternalRemoveProducts",
            value=self._open_api.api.arn_for_execute_api(
                method="PUT",
                path="/internal/projects/*/products/provisioned/*/remove",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-remove-products",
        )

        aws_cdk.CfnOutput(
            self,
            "ProvisioningApiInternalProvisioningSubnets",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/provisioning-subnets",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-provisioning-subnets",
        )

        aws_cdk.CfnOutput(
            self,
            "ProvisioningApiInternalAllProductsProvisioned",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/products/provisioned/all",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-all-products-provisioned",
        )

        self.suppress_cdk_nag(app_config=app_config)

        self.__configure_ops(app_config=app_config)

    def configure_event_buses(
        self,
        app_config: config.AppConfig,
        catalog_service_topics: list[aws_sns.ITopic],
        organization_id: str,
    ):
        self._event_bus = backend_app_event_bus.BackendAppEventBus(
            self, "domain-event-bus", app_config, event_bus_name="domain-events"
        )

        self._tools_event_bus = backend_app_event_bus.BackendAppEventBus(
            self,
            "tools-integration-event-bus",
            app_config,
            event_bus_name="tools-integration-events",
        )

        # EC2 & ECS event busses
        self._ec2_event_bus = backend_app_event_bus.BackendAppEventBus(
            self, "ec2-event-bus", app_config, event_bus_name="ec2-event-bus"
        )
        self._ecs_event_bus = backend_app_event_bus.BackendAppEventBus(
            self, "ecs-event-bus", app_config, event_bus_name="ecs-event-bus"
        )
        self._ec2_event_bus.allow_publish_from_organization(organization_id)
        self._ecs_event_bus.allow_publish_from_organization(organization_id)

        aws_logs.ResourcePolicy(
            self,
            "event-bridge-resource-policy",
            policy_statements=[
                aws_iam.PolicyStatement(
                    principals=[aws_iam.ServicePrincipal("events.amazonaws.com")],
                    actions=["logs:PutLogEvents", "logs:CreateLogStream"],
                    resources=[
                        f"{self._event_bus.event_bus_log_arn}",
                        f"{self._tools_event_bus.event_bus_log_arn}",
                    ],
                )
            ],
            resource_policy_name=app_config.format_resource_name("allow-event-bridge-publish"),
        )

        self.configure_tools_integration_event_bus(app_config, catalog_service_topics)

    def configure_tools_integration_event_bus(
        self, app_config: config.AppConfig, catalog_service_topics: list[aws_sns.ITopic]
    ):
        tools_account_id = self.get_tools_account_id(app_config)
        if tools_account_id:
            self._tools_event_bus.allow_publish_from_account(tools_account_id)

        # Pipe to forward events from the catalog service topics to the tools integration event bus
        topic_to_event_bus_pipe.TopicToEventBusPipe(
            self,
            "CatalogServiceTopicsToEventBusPipe",
            create_key=True,
            detail_type=constants.CATALOG_SERVICE_EVENTS_DETAIL_TYPE,
            description="Pipe to forward Catalog Service related events from SNS to EventBridge.",
            event_bus=self._tools_event_bus.event_bus,
            pipe_name=app_config.format_resource_name("catalog-service-pipe"),
            resources=[],  # We fetch the resources from the message
            source=constants.CATALOG_SERVICE_EVENTS_SOURCE,
            topics=catalog_service_topics,
            input_transformation=aws_pipes_alpha.InputTransformation.from_object(
                {
                    "Type": "<$.body.Type>",
                    "MessageId": "<$.body.MessageId>",
                    "TopicArn": "<$.body.TopicArn>",
                    "Subject": "<$.body.Subject>",
                    "Message": "<$.body.Message>",
                    "Timestamp": "<$.body.Timestamp>",
                }
            ),
        )

    def subscribe_to_external_events(self, app_config: config.AppConfig):
        self._tools_event_bus.add_rule_with_lambda_target(
            name="provisioning-event-rule",
            event_pattern=aws_events.EventPattern(
                source=aws_events.Match.prefix("Workbench Catalog Service"),
                detail_type=aws_events.Match.exact_string("Catalog SNS notifications"),
                detail={
                    "Subject": aws_events.Match.exact_string("AWS CloudFormation Notification"),
                    "Message": aws_events.Match.exists(),
                },
            ),
            lambda_function=self._backend_app.app_entries_functions[app_config.format_resource_name("pp-events")],
            duration_in_minutes=720,
            max_retries=3,
        )

        self._ec2_event_bus.add_rule_with_lambda_target(
            name="ec2-state-change-event-rule-v2",
            event_pattern=aws_events.EventPattern(
                source=aws_events.Match.exact_string("aws.ec2"),
                detail_type=aws_events.Match.exact_string("EC2 Instance State-change Notification"),
                detail={"state": ["stopped", "running"]},
            ),
            lambda_function=self._backend_app.app_entries_functions[app_config.format_resource_name("pp-state-events")],
            duration_in_minutes=720,
            max_retries=3,
            target_input_transformation=aws_events.RuleTargetInput.from_object(
                {
                    "version": aws_events.EventField.from_path("$.version"),
                    "id": aws_events.EventField.from_path("$.id"),
                    "detail-type": "WorkbenchEC2StateChanged",
                    "source": aws_events.EventField.from_path("$.source"),
                    "account": aws_events.EventField.from_path("$.account"),
                    "time": aws_events.EventField.from_path("$.time"),
                    "region": aws_events.EventField.from_path("$.region"),
                    "resources": aws_events.EventField.from_path("$.resources"),
                    "detail": {
                        "instanceId": aws_events.EventField.from_path("$.detail.instance-id"),
                        "state": aws_events.EventField.from_path("$.detail.state"),
                        "accountId": aws_events.EventField.from_path("$.account"),
                        "region": aws_events.EventField.from_path("$.region"),
                    },
                }
            ),
        )

        self._ecs_event_bus.add_rule_with_lambda_target(
            name="ecs-state-change-event-rule-v2",
            event_pattern=aws_events.EventPattern(
                source=aws_events.Match.exact_string("aws.ecs"),
                detail_type=aws_events.Match.exact_string("ECS Task State Change"),
                detail={
                    "lastStatus": [
                        "PROVISIONING",
                        "PENDING",
                        "ACTIVATING",
                        "RUNNING",
                        "DEACTIVATING",
                        "STOPPING",
                        "DEPROVISIONING",
                        "STOPPED",
                    ]
                },
            ),
            lambda_function=self._backend_app.app_entries_functions[app_config.format_resource_name("pp-state-events")],
            duration_in_minutes=720,
            max_retries=3,
            target_input_transformation=aws_events.RuleTargetInput.from_object(
                {
                    "version": aws_events.EventField.from_path("$.version"),
                    "id": aws_events.EventField.from_path("$.id"),
                    "detail-type": "WorkbenchContainerStateChanged",
                    "source": aws_events.EventField.from_path("$.source"),
                    "account": aws_events.EventField.from_path("$.account"),
                    "time": aws_events.EventField.from_path("$.time"),
                    "region": aws_events.EventField.from_path("$.region"),
                    "resources": aws_events.EventField.from_path("$.resources"),
                    "detail": {
                        "taskArn": aws_events.EventField.from_path("$.detail.taskArn"),
                        "clusterArn": aws_events.EventField.from_path("$.detail.clusterArn"),
                        "lastStatus": aws_events.EventField.from_path("$.detail.lastStatus"),
                        "accountId": aws_events.EventField.from_path("$.account"),
                        "region": aws_events.EventField.from_path("$.region"),
                    },
                }
            ),
        )

        self._tools_event_bus.add_rule_with_lambda_target(
            name="ecs-state-change-event-rule",
            event_pattern=aws_events.EventPattern(
                source=aws_events.Match.exact_string(
                    f"{config.ORGANIZATION_PREFIX}.{config.APPLICATION_PREFIX}.catalogservice.{app_config.environment}"
                ),
                detail_type=aws_events.Match.exact_string("WorkbenchContainerStateChanged"),
                detail={
                    "lastStatus": [
                        "PROVISIONING",
                        "PENDING",
                        "ACTIVATING",
                        "RUNNING",
                        "DEACTIVATING",
                        "STOPPING",
                        "DEPROVISIONING",
                        "STOPPED",
                    ]
                },
            ),
            lambda_function=self._backend_app.app_entries_functions[app_config.format_resource_name("pp-state-events")],
            duration_in_minutes=720,
            max_retries=3,
        )

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

    def suppress_cdk_nag(
        self,
        app_config: config.AppConfig,
    ) -> None:
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path="/ProvisioningAppStack/ProvisionedProductConfigurationStateMachine/ProvisionedProductConfigurationStateMachine/EventsRole/DefaultPolicy/Resource",
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

        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path="/ProvisioningAppStack/ec2-event-bus/event-bus-resource-policy-org",
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-EVB1",
                    reason="This is an inline policy auto-generated by CDK.",
                ),
            ],
        )

        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path="/ProvisioningAppStack/ecs-event-bus/event-bus-resource-policy-org",
            suppressions=[
                cdk_nag.NagPackSuppression(
                    id="AwsSolutions-EVB1",
                    reason="Limited to a specific organisation.",
                ),
            ],
        )

        for domain_event_handler_role_policy in [
            p
            for p in self._backend_app.app_entries_functions[self._domain_events_handler_name].role.node.children
            if isinstance(p, aws_iam.Policy)
        ]:
            cdk_nag.NagSuppressions.add_resource_suppressions(
                construct=domain_event_handler_role_policy,
                suppressions=[
                    cdk_nag.NagPackSuppression(
                        id="AwsSolutions-IAM5",
                        reason="AWS accounts will be dynamically defined in the application, thus not known.",
                        applies_to=[
                            f"Resource::arn:aws:scheduler:{app_config.region}:{app_config.account}:schedule/{app_config.bounded_context_name}/*"
                        ],
                    ),
                ],
            )

    def __configure_ops(self, app_config: config.AppConfig):
        (
            ops_monitoring.OpsMonitoringBuilder(
                self,
                app_config.format_resource_name("ops-dashboard"),
                VEW_NAMESPACE,
                VEW_SERVICE,
                app_config,
            )
            .with_lambda_functions(self._backend_app.app_entries.values())
            .with_dynamodb_table(self._storage.table)
            .with_api_gateway(self._open_api.api)
            .with_api_gateway(self._s2s_open_api.api)
            .with_command_monitoring(
                domain_module=domain,
                critical_commands=[
                    sync_provisioned_product_state_command.SyncProvisionedProductStateCommand.__name__,
                ],
            )
            .with_domain_event_monitoring(
                domain_module=domain,
                critical_events=[provisioned_product_status_out_of_sync.ProvisionedProductStatusOutOfSync.__name__],
            )
            .build()
        )

    @property
    def api(self) -> backend_app_openapi.BackendAppOpenApi:
        return self._open_api

    @property
    def s2s_api(self) -> backend_app_openapi.BackendAppOpenApi:
        return self._s2s_open_api

    @property
    def provisioning_table(self) -> backend_app_storage.BackendAppStorage:
        return self._storage

    @property
    def provisioning_table_name(self) -> str:
        return self._storage.table_name

    @property
    def provisioning_table_arn(self) -> str:
        return self._storage.table_arn

    @property
    def provisioning_entry(self) -> backend_app_entrypoints.BackendAppEntrypoints:
        return self._backend_app
