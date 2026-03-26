from urllib import parse

import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from pydantic import BaseModel

from app.authorization.adapters.query_services import (
    assignments_dynamodb_query_service,
    projects_api_query_service,
)
from app.authorization.adapters.repository import dynamo_entity_config
from app.authorization.domain.command_handlers import sync_assignments_command_handler
from app.authorization.domain.commands import sync_assignments_command
from app.authorization.domain.services.auth import authorizer
from app.authorization.entrypoints.scheduled_jobs_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    in_memory_command_bus,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
from app.shared.api import aws_api
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger
from app.shared.middleware import event_handler


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus

    class Config:
        arbitrary_types_allowed = True


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: event_handler.ScheduledJobEventResolver,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

    api_policy_stores: dict[str, authorizer.APIAuthConfig] = {}

    def __reload_config_params():
        api_policy_stores_params = parameters.get_parameters(
            path=app_config.get_policy_store_ssm_param_prefix(), force_fetch=True
        )
        for _, val in api_policy_stores_params.items():
            api_cfg_item = authorizer.APIAuthConfig.parse_raw(val)
            api_policy_stores[api_cfg_item.api_id] = api_cfg_item

    def __projects_qs_provider() -> projects_api_query_service.ProjectsApiQueryService:
        __reload_config_params()
        projects_api_url = next(
            (cfg.api_url for _, cfg in api_policy_stores.items() if cfg.bounded_context == "projects"),
            None,
        )
        if not projects_api_url:
            raise Exception("Projects BC does not have API url in it's config.")

        aws_api_instance = aws_api.AWSAPI(
            api_url=parse.urlparse(projects_api_url), region=app_config.get_default_region(), logger=logger
        )
        return projects_api_query_service.ProjectsApiQueryService(api=aws_api_instance)

    assignments_qs = assignments_dynamodb_query_service.AssignmentsDynamoDBQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_pk=app_config.get_gsi_name_inverted_pk(),
    )

    def __sync_handler(command):
        sync_assignments_command_handler.handle(
            command=command,
            projects_qs=__projects_qs_provider(),
            assignments_qs=assignments_qs,
            uow=uow,
            logger=logger,
        )

    command_bus = command_bus_metrics.CommandBusMetrics(
        inner=in_memory_command_bus.InMemoryCommandBus(logger=logger), metrics_client=metrics_client
    ).register_handler(
        sync_assignments_command.SyncAssignmentsCommand,
        __sync_handler,
    )
    return Dependencies(
        command_bus=command_bus,
    )
