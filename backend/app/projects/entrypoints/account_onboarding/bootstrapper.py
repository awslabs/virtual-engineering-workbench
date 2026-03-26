import json

import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from pydantic import BaseModel

from app.projects.adapters.query_services import dynamodb_query_service
from app.projects.adapters.repository import dynamo_entity_config
from app.projects.adapters.repository.dynamo_entity_migrations import migrations_config
from app.projects.adapters.services import (
    aws_dns_service,
    cdk_iac_service,
    ec2_network_service,
)
from app.projects.domain.command_handlers.project_accounts import (
    complete_project_account_onboarding_command_handler,
    fail_project_account_onboarding_command_handler,
    setup_dynamic_resources_command_handler,
    setup_prerequisites_resources_command_handler,
    setup_static_resources_command_handler,
)
from app.projects.domain.commands.project_accounts import (
    complete_project_account_onboarding_command,
    fail_project_account_onboarding_command,
    setup_dynamic_resources_command,
    setup_prerequisites_resources_command,
    setup_static_resources_command,
)
from app.projects.domain.model import dynamic_parameter
from app.projects.entrypoints.account_onboarding import config
from app.shared.adapters.boto import (
    aws_parameter_service,
    aws_resource_access_management_service,
    aws_secrets_service,
    aws_step_functions_service,
    boto_provider,
    orchestration_service,
)
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.query_services import ecs_task_context_query_service
from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_migrations,
    dynamodb_unit_of_work,
)
from app.shared.api import aws_events_api
from app.shared.domain.ports import task_context_query_service
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    task_context_qry_srv: task_context_query_service.TaskContextQueryService
    step_functions_service: orchestration_service.OrchestrationService

    class Config:
        arbitrary_types_allowed = True


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: boto_provider.SupportsContextManager,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=dynamodb,
        table_name=app_config.get_table_name(),
        logger=logger,
    ).register_migrations(migrations_config(gsi_entities=app_config.get_entities_gsi_name())).migrate()

    shared_uow_v2 = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

    projects_query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_inverted_primary_key_gsi_name(),
        gsi_aws_accounts=app_config.get_aws_accounts_gsi_name(),
        gsi_entities=app_config.get_entities_gsi_name(),
    )

    provider = boto_provider.BotoProvider(
        ctx=app,
        logger=logger,
        default_options=boto_provider.BotoProviderOptions(
            aws_role_name=app_config.get_dynamic_bootstrap_role(),
            aws_session_name=app_config.get_bounded_context_name(),
            aws_region=app_config.get_default_region(),
        ),
    )

    local_provider = boto_provider.BotoProvider(
        ctx=app,
        logger=logger,
        default_options=boto_provider.BotoProviderOptions(),
    )

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    dns_records = json.loads(parameters.get_parameter(app_config.get_dns_record_param_name()))

    ecs_task_context_qry_srv = ecs_task_context_query_service.EcsTaskContextQueryService(
        endpoint=app_config.get_ecs_container_metadata_uri_v4()
    )

    cdk_iac_srv = cdk_iac_service.CDKIACService(
        toolkit_stack_name=app_config.get_toolkit_stack_name(),
        toolkit_stack_qualifier=app_config.get_toolkit_stack_qualifier(),
        bootstrap_role=app_config.get_account_bootstrap_role(),
        boto_session=session,
        enable_lookup=True,
        logger=logger,
    )

    dns_srv = aws_dns_service.AWSDNSService(route53_provider=provider.client("route53"))
    param_srv = aws_parameter_service.AWSParameterService(ssm_provider=provider.client("ssm"))
    ram_srv = aws_resource_access_management_service.AWSResourceAccessManagementService(
        ram_provider=local_provider.client("ram")
    )
    secrets_srv = aws_secrets_service.AWSSecretsService(secretsmanager_provider=provider.client("secretsmanager"))

    events_client = session.client("events", region_name=app_config.get_default_region())
    events_api = aws_events_api.AWSEventsApi(client=events_client)

    message_bus = message_bus_metrics.MessageBusMetrics(
        inner=event_bridge_message_bus.EventBridgeMessageBus(
            events_api=events_api,
            event_bus_name=app_config.get_domain_event_bus_name(),
            bounded_context_name=app_config.get_bounded_context_name(),
            logger=logger,
        ),
        metrics_client=metrics_client,
        logger=logger,
    )

    sfn_service = aws_step_functions_service.AWSStepFunctionsService(
        sfn_provider=local_provider.client("stepfunctions")
    )

    network_srv = ec2_network_service.EC2NetworkService(ec2_provider=provider.client("ec2"))

    def __setup_prerequisites_resources_cmd_handler(
        command: setup_prerequisites_resources_command.SetupPrerequisitesResourcesCommand,
    ):
        return setup_prerequisites_resources_command_handler.handle(
            cmd=command,
            iac_srv=cdk_iac_srv,
        )

    def __setup_dynamic_resources_cmd_handler(
        command: setup_dynamic_resources_command.SetupDynamicResourcesCommand,
    ):
        return setup_dynamic_resources_command_handler.handle(
            cmd=command,
            dns_records=dns_records,
            dns_srv=dns_srv,
            network_srv=network_srv,
            parameter_srv=param_srv,
            parameters=[
                dynamic_parameter.DynamicParameter(
                    name=app_config.get_vpc_id_ssm_parameter_name(),
                    type=dynamic_parameter.DynamicParameterType.VPC_ID,
                    tag=app_config.get_vpc_tag(),
                ),
                dynamic_parameter.DynamicParameter(
                    name=app_config.get_backend_subnet_ids_ssm_parameter_name(),
                    type=dynamic_parameter.DynamicParameterType.BACKEND_SUBNET_IDS,
                    tag=app_config.get_backend_subnets_tag(),
                ),
                dynamic_parameter.DynamicParameter(
                    name=app_config.get_backend_subnet_cidrs_ssm_parameter_name(),
                    type=dynamic_parameter.DynamicParameterType.BACKEND_SUBNET_CIDRS,
                ),
            ],
            secrets_srv=secrets_srv,
            spoke_account_secrets_scope=app_config.get_spoke_account_secrets_scope(),
            zone_name=app_config.get_zone_name(),
        )

    def __setup_static_resources_cmd_handler(
        command: setup_static_resources_command.SetupStaticResourcesCommand,
    ):
        return setup_static_resources_command_handler.handle(
            cmd=command,
            iac_srv=cdk_iac_srv,
            ram_srv=ram_srv,
            ram_resource_tag=app_config.get_shareable_ram_resources_tag(),
        )

    def __complete_project_account_onboarding_cmd_handler(
        command: complete_project_account_onboarding_command.CompleteProjectAccountOnboarding,
    ):
        return complete_project_account_onboarding_command_handler.handle(
            command=command,
            projects_qs=projects_query_service,
            parameters_qs=param_srv,
            uow=shared_uow_v2,
            message_bus=message_bus,
            account_parameters_path=app_config.get_account_ssm_parameters_path_prefix(),
        )

    def __fail_project_account_onboarding_cmd_handler(
        command: fail_project_account_onboarding_command.FailProjectAccountOnboarding,
    ):
        return fail_project_account_onboarding_command_handler.handle(
            command=command,
            projects_qs=projects_query_service,
            uow=shared_uow_v2,
        )

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            setup_prerequisites_resources_command.SetupPrerequisitesResourcesCommand,
            __setup_prerequisites_resources_cmd_handler,
        )
        .register_handler(
            setup_dynamic_resources_command.SetupDynamicResourcesCommand,
            __setup_dynamic_resources_cmd_handler,
        )
        .register_handler(
            setup_static_resources_command.SetupStaticResourcesCommand,
            __setup_static_resources_cmd_handler,
        )
        .register_handler(
            complete_project_account_onboarding_command.CompleteProjectAccountOnboarding,
            __complete_project_account_onboarding_cmd_handler,
        )
        .register_handler(
            fail_project_account_onboarding_command.FailProjectAccountOnboarding,
            __fail_project_account_onboarding_cmd_handler,
        )
    )

    return Dependencies(
        command_bus=command_bus,
        task_context_qry_srv=ecs_task_context_qry_srv,
        step_functions_service=sfn_service,
    )
