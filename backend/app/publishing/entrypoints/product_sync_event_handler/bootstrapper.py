import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.publishing.adapters.query_services import (
    dynamodb_products_query_service,
    dynamodb_versions_query_service,
    projects_api_query_service,
)
from app.publishing.domain.command_handlers import products_versions_sync_command_handler
from app.publishing.domain.commands import products_versions_sync_command
from app.publishing.entrypoints.product_sync_event_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.api import aws_api, aws_events_api
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus

    class Config:
        arbitrary_types_allowed = True


def bootstrap(
    app_config: config.AppConfig,
    logger: logging.Logger,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    events_client = session.client("events", region_name=app_config.get_default_region())
    events_api = aws_events_api.AWSEventsApi(client=events_client)

    metrics_client = power_tools_metrics.PowerToolsMetrics()

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

    versions_qry_srv = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    aws_api_instance = aws_api.AWSAPI(
        api_url=app_config.get_projects_api_url(), region=app_config.get_default_region(), logger=logger
    )

    projects_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=aws_api_instance)

    products_qry_srv = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    def _products_versions_sync_command_factory():
        def _handle_command(command: products_versions_sync_command.ProductsVersionsSyncCommand):
            return products_versions_sync_command_handler.handle(
                command=command,
                logger=logger,
                message_bus=message_bus,
                versions_qry_srv=versions_qry_srv,
                products_qry_service=products_qry_srv,
                projects_qry_srv=projects_api_qry_srv,
            )

        return _handle_command

    command_bus = command_bus_metrics.CommandBusMetrics(
        inner=in_memory_command_bus.InMemoryCommandBus(logger=logger), metrics_client=metrics_client
    ).register_handler(
        products_versions_sync_command.ProductsVersionsSyncCommand,
        _products_versions_sync_command_factory(),
    )

    return Dependencies(command_bus=command_bus)
