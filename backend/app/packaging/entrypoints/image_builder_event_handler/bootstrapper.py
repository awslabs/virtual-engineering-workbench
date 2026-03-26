import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.packaging.adapters.query_services import (
    dynamodb_component_version_query_service,
    dynamodb_image_query_service,
    dynamodb_pipeline_query_service,
    dynamodb_recipe_query_service,
    dynamodb_recipe_version_query_service,
)
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.domain.command_handlers.image import register_image_command_handler
from app.packaging.domain.commands.image import register_image_command
from app.packaging.entrypoints.image_builder_event_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
from app.shared.api import aws_events_api
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger
from app.shared.middleware import event_handler


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    component_version_query_srv: dynamodb_component_version_query_service.DynamoDBComponentVersionQueryService
    image_query_srv: dynamodb_image_query_service.DynamoDBImageQueryService
    pipeline_query_srv: dynamodb_pipeline_query_service.DynamoDBPipelineQueryService
    recipe_version_query_srv: dynamodb_recipe_version_query_service.DynamoDBRecipeVersionQueryService

    class Config:
        arbitrary_types_allowed = True


def bootstrap(
    app_config: config.AppConfig,
    logger: logging.Logger,
    app: event_handler.EventBridgeEventResolver,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

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

    component_version_query_srv = dynamodb_component_version_query_service.DynamoDBComponentVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_status_key(),
    )

    image_query_srv = dynamodb_image_query_service.DynamoDBImageQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_custom_query_by_build_version_arn=app_config.get_gsi_name_query_by_build_version_arn(),
        gsi_custom_query_by_recipe_id_and_version=app_config.get_gsi_name_query_by_recipe_id_and_version(),
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_name_image_upstream_id=app_config.get_gsi_name_image_upstream_id(),
    )

    pipeline_query_srv = dynamodb_pipeline_query_service.DynamoDBPipelineQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_primary_key(),
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    recipe_query_srv = dynamodb_recipe_query_service.DynamoDBRecipeQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    recipe_version_query_srv = dynamodb_recipe_version_query_service.DynamoDBRecipeVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_status_key(),
    )

    def _register_image_command_handler_factory():
        def _handle(command):
            register_image_command_handler.handle(
                command=command,
                component_version_qry_srv=component_version_query_srv,
                image_qry_srv=image_query_srv,
                message_bus=message_bus,
                pipeline_qry_srv=pipeline_query_srv,
                recipe_qry_srv=recipe_query_srv,
                recipe_version_qry_srv=recipe_version_query_srv,
                uow=uow,
            )

        return _handle

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    command_bus = command_bus_metrics.CommandBusMetrics(
        inner=in_memory_command_bus.InMemoryCommandBus(logger=logger), metrics_client=metrics_client
    ).register_handler(
        register_image_command.RegisterImageCommand,
        _register_image_command_handler_factory(),
    )

    return Dependencies(
        command_bus=command_bus,
        component_version_query_srv=component_version_query_srv,
        image_query_srv=image_query_srv,
        pipeline_query_srv=pipeline_query_srv,
        recipe_version_query_srv=recipe_version_query_srv,
    )
