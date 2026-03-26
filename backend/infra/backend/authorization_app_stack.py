import json

import aws_cdk
import constructs
from aws_cdk import aws_dynamodb, aws_events, aws_events_targets, aws_iam, aws_ssm

from app.authorization import domain
from app.authorization.domain.commands import sync_assignments_command
from infra import config, constants
from infra.constructs import backend_app_entrypoints, backend_app_storage, shared_layer
from infra.constructs.eventbridge import l3_event_bus
from infra.helpers import ops_monitoring

VEW_NAMESPACE = "VirtualEngineeringWorkbench"
VEW_SERVICE = "Authorization"
GSI_NAME_INVERTED_PK = "gsi_inverted_primary_key"


class AuthorizationAppStack(aws_cdk.Stack):
    def __init__(
        self,
        scope: constructs.Construct,
        id: str,
        app_config: config.AppConfig,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Lambda layers
        self.__authorization_app_layer = shared_layer.SharedLayer(
            self,
            "AuthorizationAppLayer",
            layer_version_name="authorization_app_libraries",
            entry="app/authorization/libraries",
        )
        self.__shared_app_layer = shared_layer.SharedLayer(
            self,
            "SharedAppLayer",
            layer_version_name="shared_app_libraries",
            entry="app/shared",
        )

        log_level = "DEBUG" if app_config.environment in ["dev", "qa"] else "INFO"

        parsed_user_role_stage_access = app_config.environment_config["user-role-stage-access"]
        user_role_stage_access_param_name = app_config.format_ssm_parameter_name("user-role-stage-access")
        user_role_stage_access_param = aws_ssm.StringParameter(
            self,
            "StageAccessConfig",
            parameter_name=user_role_stage_access_param_name,
            string_value=json.dumps(parsed_user_role_stage_access),
            type=aws_ssm.ParameterType.STRING,
        )
        policy_param_prefix = app_config.format_ssm_parameter_name(
            constants.AUTH_BC_POLICY_STORE_SSM_PARAM.format(bc_name="")
        )

        storage = backend_app_storage.BackendAppStorage(self, "AuthorizationAppStorage", app_config)

        storage.table.add_global_secondary_index(
            index_name=GSI_NAME_INVERTED_PK,
            partition_key=aws_dynamodb.Attribute(name="SK", type=aws_dynamodb.AttributeType.STRING),
            sort_key=aws_dynamodb.Attribute(name="PK", type=aws_dynamodb.AttributeType.STRING),
        )

        authorizer_function_name = app_config.format_resource_name("authorizer-request-events")
        projects_events_handler_name = app_config.format_resource_name("projects-events")
        scheduled_jobs_handler_name = app_config.format_resource_name("scheduled-jobs")

        user_pool_url = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-url-ssm-param"].format(environment=app_config.environment),
        )

        user_pool_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-userpool-id-ssm-param"].format(environment=app_config.environment),
        )

        user_pool_client_id = aws_ssm.StringParameter.value_for_string_parameter(
            self,
            app_config.environment_config["cognito-userpool-client-ids-ssm-param"].format(
                environment=app_config.environment
            ),
        )

        user_pool_region = app_config.environment_config["cognito-region"]

        common_env_vars = {
            "BOUNDED_CONTEXT": app_config.bounded_context_name,
            "LOG_LEVEL": log_level,
            "POWERTOOLS_METRICS_NAMESPACE": VEW_NAMESPACE,
            "POWERTOOLS_SERVICE_NAME": VEW_SERVICE,
            "TABLE_NAME": storage.table.table_name,
            "GSI_NAME_INVERTED_PK": GSI_NAME_INVERTED_PK,
            "POLICY_STORE_SSM_PARAM_PREFIX": policy_param_prefix,
        }

        # Create shared authorizer function using BackendAppEntrypoints
        self.__backend_app = backend_app_entrypoints.BackendAppEntrypoints(
            self,
            "AuthorizationApp",
            app_entry_points=[
                backend_app_entrypoints.AppEntryPoint(
                    name=authorizer_function_name,
                    app_root="app",
                    lambda_root="app/authorization",
                    entry="app/authorization/entrypoints/api_gateway_authorizer_request_event_handler",
                    environment={
                        **common_env_vars,
                        "APP_ENVIRONMENT": app_config.environment,
                        "USER_POOL_URL": f"https://{user_pool_url}",
                        "USER_POOL_ID": user_pool_id,
                        "USER_POOL_CLIENT_IDS": user_pool_client_id,
                        "USER_POOL_REGION": user_pool_region,
                        "JWKS_URI": f"https://cognito-idp.{user_pool_region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json",
                        "JWK_TIMEOUT": "3",
                        "USER_ROLE_STAGE_ACCESS_SSM_PARAM": user_role_stage_access_param_name,
                    },
                    permissions=[
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "verifiedpermissions:IsAuthorized",
                                    "verifiedpermissions:ListPolicies",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[f"arn:aws:verifiedpermissions::{app_config.account}:policy-store/*"],
                            )
                        ),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "ssm:GetParametersByPath",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:ssm:{app_config.region}:{app_config.account}:parameter{policy_param_prefix}",
                                ],
                            )
                        ),
                        lambda lambda_f: user_role_stage_access_param.grant_read(lambda_f),
                        lambda lambda_f: storage.table.grant_read_data(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific.get(
                        "api-gateway-event-lambda-reserved-concurrency"
                    ),
                    provisioned_concurrency=app_config.component_specific.get(
                        "api-gateway-event-lambda-provisioned-concurrency"
                    ),
                    timeout=aws_cdk.Duration.seconds(5),
                    memory_size=1792,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=projects_events_handler_name,
                    app_root="app",
                    lambda_root="app/authorization",
                    entry="app/authorization/entrypoints/projects_event_handler",
                    environment=common_env_vars,
                    permissions=[
                        lambda lambda_f: storage.table.grant_read_write_data(lambda_f),
                    ],
                    reserved_concurrency=app_config.component_specific["projects-events-lambda-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.seconds(30),
                    memory_size=256,
                    asynchronous=True,
                ),
                backend_app_entrypoints.AppEntryPoint(
                    name=scheduled_jobs_handler_name,
                    app_root="app",
                    lambda_root="app/authorization",
                    entry="app/authorization/entrypoints/scheduled_jobs_handler",
                    environment=common_env_vars,
                    permissions=[
                        lambda lambda_f: storage.table.grant_read_write_data(lambda_f),
                        lambda lambda_f: lambda_f.add_to_role_policy(
                            statement=aws_iam.PolicyStatement(
                                actions=[
                                    "ssm:GetParametersByPath",
                                ],
                                effect=aws_iam.Effect.ALLOW,
                                resources=[
                                    f"arn:aws:ssm:{app_config.region}:{app_config.account}:parameter{policy_param_prefix}",
                                ],
                            )
                        ),
                    ],
                    reserved_concurrency=app_config.component_specific["scheduled-jobs-lambda-reserved-concurrency"],
                    provisioned_concurrency=None,
                    timeout=aws_cdk.Duration.minutes(15),
                    memory_size=1792,
                    asynchronous=True,
                ),
            ],
            app_layers=[
                self.__authorization_app_layer.layer,
                self.__shared_app_layer.layer,
            ],
        )

        # Subscribe to integration events
        projects_event_bus = l3_event_bus.from_bounded_context(
            self, "projects-bus", app_config=app_config, bounded_context_name="projects"
        )
        projects_event_bus.subscribe_to_events(
            name="projects-events-rule",
            lambda_function=self.__backend_app.app_entries_functions[projects_events_handler_name],
            events=[
                "EnrolmentApproved",
                "UserAssigned",
                "UserReAssigned",
                "UserUnAssigned",
            ],
        )

        # Scheduled jobs
        aws_events.Rule(
            self,
            "sync-scheduler-rule",
            schedule=aws_events.Schedule.cron(minute="0", hour="8", month="*", week_day="SAT"),
            targets=[
                aws_events_targets.LambdaFunction(
                    self.__backend_app.app_entries_functions[scheduled_jobs_handler_name],
                    event=aws_events.RuleTargetInput.from_object({"jobName": "AssignmentsSyncJob"}),
                )
            ],
            rule_name=app_config.format_resource_name("sync-job"),
        )

        aws_ssm.StringParameter(
            self,
            "AuthorizerArn",
            parameter_name=app_config.format_ssm_parameter_name(constants.AUTH_BC_HANDLER_PARAM_NAME),
            string_value=self.__backend_app.app_entries_function_aliases[authorizer_function_name].function_arn,
            description="Authorization BC Lambda function ARN to be used as API authorizer",
        )

        aws_ssm.StringParameter(
            self,
            "AuthorizerRoleArn",
            parameter_name=app_config.format_ssm_parameter_name(constants.AUTH_BC_HANDLER_ROLE_PARAM_NAME),
            string_value=self.__backend_app.app_entries_function_aliases[authorizer_function_name].role.role_arn,
            description="Authorization BC Lambda function role ARN to be used to grant API access to Bounded Contexts",
        )

        aws_cdk.CfnOutput(
            self,
            "APIGatewayAuthorizerRequestEventHandlerName",
            value=self.__backend_app.app_entries_functions[authorizer_function_name].role.role_arn,
            export_name="api-gateway-authorizer-request-event-handler",
        )

        aws_cdk.CfnOutput(
            self,
            "APIGatewayAuthorizerRequestEventHandlerRoleArn",
            value=self.__backend_app.app_entries_functions[authorizer_function_name].role.role_arn,
            export_name=constants.AUTH_BC_HANDLER_ROLE_ARN_EXPORT_NAME,
        )

        aws_cdk.CfnOutput(
            self,
            "APIGatewayAuthorizerScheduledJobsRoleArn",
            value=self.__backend_app.app_entries_functions[scheduled_jobs_handler_name].role.role_arn,
            export_name=constants.AUTH_BC_SCHEDULED_JOB_HANDLER_ROLE_ARN_EXPORT_NAME,
        )

        self.__configure_ops(app_config, storage)

    def __configure_ops(self, app_config: config.AppConfig, storage: backend_app_storage.BackendAppStorage):
        (
            ops_monitoring.OpsMonitoringBuilder(
                self,
                app_config.format_resource_name("ops-dashboard"),
                VEW_NAMESPACE,
                VEW_SERVICE,
                app_config,
            )
            .with_lambda_functions(self.__backend_app.app_entries.values())
            .with_dynamodb_table(storage.table)
            .with_command_monitoring(
                domain_module=domain, critical_commands=[sync_assignments_command.SyncAssignmentsCommand.__name__]
            )
            .with_domain_event_monitoring(domain_module=domain)
            .build()
        )
