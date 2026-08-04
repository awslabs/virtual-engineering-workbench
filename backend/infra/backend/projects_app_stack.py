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
    aws_events_targets,
    aws_iam,
    aws_scheduler,
    aws_ssm,
)

from app.projects import domain
from infra import config, constants
from infra.auth import projects_auth, projects_auth_schema
from infra.backend import vew_bounded_context_stack
from infra.constructs import (
    backend_app_api_auth,
    backend_app_ecs_cluster,
    backend_app_entrypoints,
    backend_app_event_bus,
    backend_app_openapi,
    backend_app_openapi_oauth,
    backend_app_storage,
    backend_app_task_definition,
    shared_layer,
)
from infra.constructs.account_onboarding import account_onboarding_state_machine
from infra.helpers import ops_monitoring

# Global variables
GSI_ATTRIBUTE_NAME_ENTITY = "entity"
GSI_ATTRIBUTE_NAME_QPK = "QPK"
GSI_ATTRIBUTE_NAME_QSK = "QSK"
GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"
GSI_NAME_AWS_ACCOUNTS = "gsi_aws_accounts"
GSI_NAME_ENTITIES = "gsi_entities"
GSI_NAME_QPK = "gsi_query_pk"
GSI_NAME_QSK = "gsi_query_sk"
VEW_SERVICE = "Projects"


class Entrypoint(enum.StrEnum):
    API = "api"
    DOMAIN_EVENT_HANDLER = "domain-event-handler"
    S2S_API = "s2s-api"
    SCHEDULED_METRIC_PRODUCER = "scheduled-metric-producer"
    ACCOUNT_ONBOARDING = "account-onboarding"


class ProjectsAppStack(vew_bounded_context_stack.VEWBoundedContextStack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        custom_api_domain: typing.Optional[str],
        organization_id: str,
        image_service_account_id: str,
        catalog_service_account_id: str,
        ci_commit_sha: str,
        qualifier: str,
        provision_private_endpoint: bool = False,
        vpc_endpoint: aws_ec2.IVpcEndpoint | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, app_config=app_config, **kwargs)

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

        dns_records = aws_ssm.StringParameter.from_string_parameter_name(
            self,
            "DNSRecords",
            string_parameter_name=app_config.environment_config["dns-records-param"].format(
                environment=app_config.environment
            ),
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
            "ProjectsAppStorage",
            app_config,
            enable_streaming=True,
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_INVERTED_PK,
            partition_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="PK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_AWS_ACCOUNTS,
            partition_key=aws_dynamodb.Attribute(name="awsAccountId", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_ENTITIES,
            partition_key=aws_dynamodb.Attribute(
                name=GSI_ATTRIBUTE_NAME_ENTITY, type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(name="PK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_QPK,
            partition_key=aws_dynamodb.Attribute(name=GSI_ATTRIBUTE_NAME_QPK, type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
        )
        self._storage.table.add_global_secondary_index(
            index_name=GSI_NAME_QSK,
            partition_key=aws_dynamodb.Attribute(name="PK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name=GSI_ATTRIBUTE_NAME_QSK, type=aws_dynamodb.AttributeType.STRING),
        )

        # Lambda functions
        self._projects_app_layer = shared_layer.SharedLayer(
            self,
            "ProjectsAppLayer",
            layer_version_name="projects_app_libraries",
            entry="app/projects/libraries",
        )
        self._shared_app_layer = shared_layer.SharedLayer(
            self,
            "SharedAppLayer",
            layer_version_name="shared_app_libraries",
            entry="app/shared",
        )

        scheduled_metric_producer_name = app_config.format_resource_name(Entrypoint.SCHEDULED_METRIC_PRODUCER)
        account_onboarding_handler_name = app_config.format_resource_name(Entrypoint.ACCOUNT_ONBOARDING)

        # Cognito user pool ID — needed both by the UI API Lambda (to enrich
        # newly-assigned members with their email on onboarding) and by the
        # S2S API's OAuth integration below.
        cognito_user_pool_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-userpool-id-ssm-param"].format(environment=app_config.environment),
        )
        cognito_user_pool_arn = f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{cognito_user_pool_id}"

        environment_vars = {
            "TABLE_NAME": self._storage.table.table_name,
            "DOMAIN_EVENT_BUS_ARN": self._event_bus.event_bus_arn,
            "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
            "GSI_NAME_AWS_ACCOUNTS": GSI_NAME_AWS_ACCOUNTS,
            "GSI_NAME_ENTITIES": GSI_NAME_ENTITIES,
            "GSI_NAME_QPK": GSI_NAME_QPK,
            "GSI_NAME_QSK": GSI_NAME_QSK,
            "POWERTOOLS_SERVICE_NAME": VEW_SERVICE,
        }
        environment_vars_acct_onboard = {
            "ACCOUNT_SSM_PARAMETERS_PATH_PREFIX": app_config.format_ssm_parameter_name(
                component_name=constants.PROJECTS_SPOKE_ACCOUNT_SSM_PARAMETER_SCOPE,
                name=None,
                include_environment=False,
            ),
            "ACCOUNT_BOOTSTRAP_ROLE": constants.PROJECTS_ACCOUNT_BOOTSTRAP_ROLE,
            "DNS_RECORDS_PARAM_NAME": dns_records.parameter_name,
            "DYNAMIC_BOOTSTRAP_ROLE": constants.PROJECTS_DYNAMIC_BOOTSTRAP_ROLE,
            "SHAREABLE_RAM_RESOURCES_TAG": constants.RESOURCE_ACCESS_MANAGEMENT_TAG_NAME,
            "VPC_ID_SSM_PARAMETER_NAME": app_config.environment_config["spoke-account-vpc-id-param-name"],
            "VPC_TAG": app_config.environment_config["spoke-account-vpc-tag"],
            "BACKEND_SUBNET_IDS_SSM_PARAMETER_NAME": app_config.environment_config[
                "spoke-account-backend-subnet-ids-param-name"
            ],
            "BACKEND_SUBNET_TAG": app_config.environment_config["spoke-account-backend-subnet-tag"],
            "BACKEND_SUBNET_CIDRS_SSM_PARAMETER_NAME": app_config.environment_config[
                "spoke-account-backend-subnet-cidrs-param-name"
            ],
        }

        self._backend_app = backend_app_entrypoints.BackendAppEntrypoints(
            self,
            "ProjectsApp",
            app_config=app_config,
            global_env_vars=environment_vars,
            app_entry_points=[
                backend_app_entrypoints.AppEntryPoint(
                    name=app_config.format_resource_name(Entrypoint.API),
                    app_root="app",
                    lambda_root="app/projects",
                    entry="app/projects/entrypoints/api",
                    environment={
                        "AUDIT_LOGGING_KEY_NAME": audit_logging_key_name,
                        "API_BASE_PATH": constants.CUSTOM_DNS_API_PATH_PROJECTS,
                        "STRIP_PREFIXES": f"{constants.CUSTOM_DNS_API_PATH_PROJECTS},{constants.CUSTOM_DNS_IAM_API_PATH_PROJECTS}",
                        "WEB_APPLICATION_ACCOUNT_ID": app_config.account,
                        "WEB_APPLICATION_ENVIRONMENT": app_config.environment,
                        "IMAGE_SERVICE_ACCOUNT_ID": image_service_account_id,
                        "CATALOG_SERVICE_ACCOUNT_ID": catalog_service_account_id,
                        "CUSTOM_DNS": custom_api_domain,
                        "LAYER_VERSION": self._shared_app_layer.layer.layer_version_arn,
                        "COGNITO_USER_POOL_ID": cognito_user_pool_id,
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
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=["cloudwatch:GetMetricData"],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    "*",
                                ],
                            )
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=["cognito-idp:ListUsers"],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[cognito_user_pool_arn],
                            )
                        ),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["api-lambda-reserved-concurrency"],
                    provisioned_concurrency=app_config.component_specific["api-lambda-provisioned-concurrency"],
                    timeout=aws_cdk.Duration.seconds(5),
                    memory_size=1792,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=app_config.format_resource_name(Entrypoint.DOMAIN_EVENT_HANDLER),
                    app_root="app",
                    lambda_root="app/projects",
                    entry="app/projects/entrypoints/domain_event_handler",
                    environment={
                        "ENABLED_WORKBENCH_REGIONS": ",".join(
                            app_config.environment_config["enabled-workbench-regions"]
                        ),
                    },
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["domain-event-handler-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.minutes(5),
                    memory_size=1792,
                    asynchronous=True,
                    vpc_name=app_config.environment_config["vpc-name"],
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=app_config.format_resource_name(Entrypoint.S2S_API),
                    app_root="app",
                    lambda_root="app/projects",
                    entry="app/projects/entrypoints/s2s_api",
                    environment={
                        "AUDIT_LOGGING_KEY_NAME": audit_logging_key_name,
                        "API_BASE_PATH": constants.CUSTOM_DNS_S2S_API_PATH_PROJECTS,
                        "STRIP_PREFIXES": constants.CUSTOM_DNS_S2S_API_PATH_PROJECTS,
                        "COGNITO_USER_POOL_ID": cognito_user_pool_id,
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
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=["cognito-idp:ListUsers"],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[cognito_user_pool_arn],
                            )
                        ),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["api-lambda-reserved-concurrency"],
                    provisioned_concurrency=app_config.component_specific["api-lambda-provisioned-concurrency"],
                    timeout=aws_cdk.Duration.seconds(5),
                    memory_size=256,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=scheduled_metric_producer_name,
                    app_root="app",
                    lambda_root="app/projects",
                    entry="app/projects/entrypoints/scheduled_metric_producer",
                    environment={},
                    permissions=[
                        lambda lambda_f: self._storage.table.grant_read_data(lambda_f),
                    ],
                    reserved_concurrency=None,
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(10),
                    memory_size=256,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=account_onboarding_handler_name,
                    app_root="app",
                    lambda_root="app/projects",
                    entry="app/projects/entrypoints/account_onboarding",
                    environment={
                        **environment_vars_acct_onboard,
                        "SPOKE_ACCOUNT_SECRETS_SCOPE": constants.PROJECTS_SPOKE_ACCOUNT_SECRETS_SCOPE,
                        "ZONE_NAME": app_config.component_specific["zone-name"],
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
                                    f"arn:aws:iam::*:role/{constants.PROJECTS_ACCOUNT_BOOTSTRAP_ROLE}",
                                    f"arn:aws:iam::*:role/{constants.PROJECTS_DYNAMIC_BOOTSTRAP_ROLE}",
                                ],
                            ),
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "secretsmanager:GetSecretValue",
                                    "secretsmanager:DescribeSecret",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:*",
                                ],
                            ),
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "secretsmanager:ListSecrets",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=["*"],
                            ),
                        ),
                        lambda lambda_f: dns_records.grant_read(lambda_f),
                        lambda lambda_f: self._storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: self._event_bus.grant_put_events_to(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["account-onboarding-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=1792,
                    asynchronous=True,
                ),
            ],
            app_layers=[
                self._projects_app_layer.layer,
                self._shared_app_layer.layer,
            ],
        ).with_access_token_tag(app_config.environment_config.get("role-access-token", None))

        # Task definitions
        ecs_cluster_vpc_name = app_config.environment_config["vpc-name"]
        ecs_cluster_vpc = aws_ec2.Vpc.from_lookup(self, "ProjectsEcsClusterVpc", vpc_name=ecs_cluster_vpc_name)
        self.__ecs_cluster = backend_app_ecs_cluster.BackendAppEcsCluster(
            self,
            "ProjectsEcsCluster",
            cluster_name=app_config.format_resource_name("ecs-cluster"),
            vpc=ecs_cluster_vpc,
        )
        # Use pre-built image from CI, or build from source with Docker locally
        usecase_cdk_app_dir = "infra/backend/resources/projects_app_stack/usecase_cdk_app"
        use_prebuilt_image = ci_commit_sha != "latest"

        self.__usecase_cdk_app_task_definition = backend_app_task_definition.BackendAppTaskDefinition(
            self,
            "ProjectsUsecaseCdkAppTaskDefinition",
            container_name=app_config.format_resource_name("usecase-cdk-app"),
            cpu_task=4096,
            environment={
                **backend_app_entrypoints.BackendAppEntrypoints.build_global_env_vars(app_config),
                **environment_vars,
                **environment_vars_acct_onboard,
                "TOOLKIT_STACK_NAME": constants.PROJECTS_TOOLKIT_STACK_NAME,
                "TOOLKIT_STACK_QUALIFIER": constants.PROJECTS_TOOLKIT_STACK_QUALIFIER,
            },
            image=(
                f"{self.account}.dkr.ecr.{self.region}.{self.url_suffix}/cdk-{qualifier}-container-assets-{self.account}-{self.region}:usecase-{ci_commit_sha}"
                if use_prebuilt_image
                else None
            ),
            directory=None if use_prebuilt_image else usecase_cdk_app_dir,
            include=(
                []
                if use_prebuilt_image
                else [
                    "app/projects/**",
                    "app/shared/**",
                    "app/usecase/**",
                    "infra/constructs/**",
                    "infra/usecase/**",
                    "infra/__init__.py",
                    "infra/config.py",
                    "infra/constants.py",
                    "cdk-usecase.json",
                    "usecase_app.py",
                ]
            ),
            execution_role_name=app_config.format_resource_name("usecase-cdk-app-execution"),
            memory_limit_mib_task=8192,
            permissions=[
                lambda task_definition: task_definition.add_to_execution_role_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:BatchGetImage",
                            "ecr:GetDownloadUrlForLayer",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=[
                            f"arn:aws:ecr:{self.region}:{self.account}:repository/cdk-{qualifier}-container-assets-{self.account}-{self.region}"
                        ],
                    )
                ),
                lambda task_definition: task_definition.add_to_execution_role_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ecr:GetAuthorizationToken",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                    )
                ),
                lambda task_definition: task_definition.add_to_task_role_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "sts:AssumeRole",
                            "sts:TagSession",
                        ],
                        conditions={"StringEquals": {"aws:ResourceOrgID": organization_id}},
                        effect=aws_iam.Effect.ALLOW,
                        resources=[f"arn:aws:iam::*:role/{constants.PROJECTS_ACCOUNT_BOOTSTRAP_ROLE}"],
                    )
                ),
                lambda task_definition: task_definition.add_to_task_role_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ram:AssociateResourceShare",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                        conditions={
                            "StringEquals": {f"ram:ResourceTag/{constants.RESOURCE_ACCESS_MANAGEMENT_TAG_NAME}": "true"}
                        },
                    )
                ),
                lambda task_definition: task_definition.add_to_task_role_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ssm:PutResourcePolicy",
                            "ssm:GetResourcePolicies",
                            "ssm:DeleteResourcePolicy",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                        conditions={
                            "StringEquals": {f"aws:ResourceTag/{constants.RESOURCE_ACCESS_MANAGEMENT_TAG_NAME}": "true"}
                        },
                    )
                ),
                lambda task_definition: task_definition.add_to_task_role_policy(
                    statement=aws_iam.PolicyStatement(
                        actions=[
                            "ram:GetResourceShares",
                            "states:SendTaskFailure",
                        ],
                        effect=aws_iam.Effect.ALLOW,
                        resources=["*"],
                    )
                ),
                lambda task_definition: dns_records.grant_read(task_definition.task_role),
                lambda task_definition: self._storage.table.grant_read_write_data(task_definition.task_role),
            ],
            task_definition_name=app_config.format_resource_name("usecase-cdk-app"),
            task_role_name=app_config.format_resource_name("usecase-cdk-app-task"),
        )

        # Account on-boarding state machine
        self.__onboarding_state_machine = account_onboarding_state_machine.AccountOnboardingStateMachine(
            self,
            "AccountOnboardingStateMachine",
            app_config=app_config,
            account_onboarding_lambda=self._backend_app.app_entries_functions[account_onboarding_handler_name],
            ecs_cluster=self.__ecs_cluster.ecs_cluster,
            task_definition=self.__usecase_cdk_app_task_definition.task_definition,
        )

        self._event_bus.l3_event_bus.subscribe_to_events(
            name="account-onboarding-event-rule",
            state_machine=self.__onboarding_state_machine.state_machine,
            events=["accountonboarding-request"],
        )

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
            "ProjectsAppOpenApi",
            app_config,
            handler=self._backend_app.app_entries_function_aliases[app_config.format_resource_name(Entrypoint.API)],
            schema_directory="app/projects/entrypoints/api/schema/",
            schema="proserve-workbench-projects-api-schema.yaml",
            api_version="v1",
            version_description="First release of Project API",
            cache_enabled=False,
            waf_acl_arn=api_acl_arn,
            cache_explicit_disable=[
                "/projects/{projectId}/accounts/GET",
                "/projects/{projectId}/users/GET",
                "/projects/{projectId}/users/{userId}/GET",
                "/projects/{projectId}/enrolments/GET",
                "/projects/{projectId}/technologies/GET",
                "/projects/GET",
                "/projects/{projectId}/GET",
            ],
            custom_domain=custom_api_domain,
            base_path=constants.CUSTOM_DNS_API_PATH_PROJECTS,
            endpoint_type=(
                aws_apigateway.EndpointType.PRIVATE
                if provision_private_endpoint
                else aws_apigateway.EndpointType.REGIONAL
            ),
            vpc_endpoint=vpc_endpoint if provision_private_endpoint else None,
            cedar_policy_config=backend_app_api_auth.CedarPolicyConfig(
                cedar_schema=projects_auth_schema.projects_schema,
                cedar_policies=projects_auth.projects_bc_auth_policies,
                entity_resolution_apis=["/internal/user/assignments"],
            ),
            provision_iam_api=True,
            iam_role_access=config.VEWRole.PLATFORM_USER,
        )

        # API Gateway for service to service access
        self._s2s_open_api = backend_app_openapi_oauth.BackendAppOpenApiOauth(
            self,
            "ServiceIntegrationProjectsOpenApi",
            app_config,
            handler=self._backend_app.app_entries_function_aliases[app_config.format_resource_name(Entrypoint.S2S_API)],
            schema_directory="app/projects/entrypoints/s2s_api/schema/",
            schema="proserve-workbench-s2s-projects-api-schema.yaml",
            api_version="v1",
            version_description="First release of service to service Project API",
            user_pool_id=cognito_user_pool_id,
            cache_enabled=True,
            waf_acl_arn=api_acl_arn if not provision_private_endpoint else None,
            cache_explicit_disable=[
                "/projects/GET",
            ],
            endpoint_type=(
                aws_apigateway.EndpointType.PRIVATE
                if provision_private_endpoint
                else aws_apigateway.EndpointType.REGIONAL
            ),
            vpc_endpoint=vpc_endpoint if provision_private_endpoint else None,
        )

        # Metrics scheduler
        aws_events.Rule(
            self,
            "metrics-scheduler-rule",
            schedule=aws_events.Schedule.cron(minute="*/5"),  # every 5 mins
            targets=[
                aws_events_targets.LambdaFunction(
                    self._backend_app.app_entries_functions[scheduled_metric_producer_name]
                )
            ],
            rule_name=app_config.format_resource_name(Entrypoint.SCHEDULED_METRIC_PRODUCER),
        )

        # --- Legacy export: kept for backward compatibility during migration. ---
        # --- Was consumed by integration_permissions_stack.py (now replaced by ServiceDiscoveryStack). ---
        # --- Safe to remove once the old CloudFormation stack is deleted. ---
        aws_cdk.CfnOutput(
            self,
            "ProjectsApiInternalUserAssignments",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/user/assignments",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-user-assignments",
        )

        aws_cdk.CfnOutput(
            self,
            "ProjectsApiInternalProjectAssignments",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/projects/*/users",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-project-assignments",
        )

        aws_cdk.CfnOutput(
            self,
            "ProjectsApiInternalProjects",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/projects",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-projects",
        )

        aws_cdk.CfnOutput(
            self,
            "ProjectsApiInternalUsers",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/users",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-users",
        )

        aws_cdk.CfnOutput(
            self,
            "ProjectsApiInternalAccounts",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/accounts",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-accounts",
        )

        aws_cdk.CfnOutput(
            self,
            "ProjectsApiInternalProjectAssignment",
            value=self._open_api.api.arn_for_execute_api(
                method="GET",
                path="/internal/projects/*/users/*",
                stage=self._open_api.api.deployment_stage.stage_name,
            ),
            export_name=f"{app_config.component_name}-api-internal-project-assignment",
        )

        # --- End legacy exports ---

        # Stack based suppressions
        cdk_nag.NagSuppressions.add_resource_suppressions_by_path(
            stack=aws_cdk.Stack.of(self),
            path="/ProjectsAppStack/AccountOnboardingStateMachine/AccountOnboardingStateMachine/EventsRole/DefaultPolicy/Resource",
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

        self._event_bus.l3_event_bus.subscribe_to_events(
            name="packaging-domain-events-rule",
            lambda_function=self._backend_app.app_entries_functions[
                app_config.format_resource_name(Entrypoint.DOMAIN_EVENT_HANDLER)
            ],
            events=[
                "EnrolmentApproved",
                "ProjectAccountOnBoarded",
                "UserAssigned",
            ],
        )

        self.__configure_ops(app_config=app_config)

    def configure_event_buses(self, app_config: config.AppConfig):
        self._event_bus = backend_app_event_bus.BackendAppEventBus(
            self, "domain-event-bus", app_config, event_bus_name="domain-events"
        )
        self._tools_event_bus = backend_app_event_bus.BackendAppEventBus(
            self,
            "tools-integration-event-bus",
            app_config,
            event_bus_name="tools-integration-events",
        )

        self.configure_tools_integration_event_bus(app_config)

    def configure_tools_integration_event_bus(self, app_config: config.AppConfig):
        if app_config.environment_config["tools-account-id-ssm-param"]:
            account_on_boarding_account = aws_ssm.StringParameter.from_string_parameter_name(
                self,
                "account_on_boarding_account",
                string_parameter_name=app_config.environment_config["tools-account-id-ssm-param"].format(
                    environment=app_config.environment
                ),
            ).string_value

            self._tools_event_bus.allow_publish_from_account(account_on_boarding_account)

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
            .with_api_gateway(self._s2s_open_api.api)
            .with_step_functions([self.__onboarding_state_machine.state_machine])
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
    def s2s_api(self) -> backend_app_openapi.BackendAppOpenApi:
        return self._s2s_open_api

    @property
    def project_table(self) -> backend_app_storage.BackendAppStorage:
        return self._storage

    @property
    def project_table_name(self) -> str:
        return self._storage.table_name

    @property
    def project_table_arn(self) -> str:
        return self._storage.table_arn

    @property
    def project_entry(self) -> backend_app_entrypoints.BackendAppEntrypoints:
        return self._backend_app
