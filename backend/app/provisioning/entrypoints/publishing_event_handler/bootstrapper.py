from typing import Callable

import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.provisioning.adapters.query_services import (
    dynamodb_products_query_service,
    dynamodb_provisioned_products_query_service,
    dynamodb_versions_query_service,
    publishing_api_query_service,
)
from app.provisioning.adapters.repository import dynamo_entity_config
from app.provisioning.adapters.repository.dynamo_entity_migrations import (
    migrations_config,
)
from app.provisioning.domain.command_handlers.product_provisioning import (
    check_if_upgrade_available,
)
from app.provisioning.domain.commands.product_provisioning import (
    check_if_upgrade_available_command,
)
from app.provisioning.domain.event_handlers import (
    update_product_read_model_event_handler,
    update_recommended_version_handler,
)
from app.provisioning.domain.read_models import product
from app.provisioning.entrypoints.publishing_event_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_migrations,
    dynamodb_unit_of_work,
)
from app.shared.api import aws_api, aws_events_api
from app.shared.ddd import aggregate
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    update_product_read_model_event_handler: Callable
    update_recommended_version_read_model_event_handler: Callable

    class Config:
        arbitrary_types_allowed = True


def bootstrap(  # noqa: C901
    app_config: config.AppConfig,
    logger: logging.Logger,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    shared_uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

    events_client = session.client("events", region_name=app_config.get_default_region())
    events_api = aws_events_api.AWSEventsApi(client=events_client)
    metrics_client = power_tools_metrics.PowerToolsMetrics()

    mb = message_bus_metrics.MessageBusMetrics(
        inner=event_bridge_message_bus.EventBridgeMessageBus(
            events_api=events_api,
            event_bus_name=app_config.get_domain_event_bus_name(),
            bounded_context_name=app_config.get_bounded_context_name(),
            logger=logger,
        ),
        metrics_client=metrics_client,
        logger=logger,
    )

    versions_query_service = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        dynamodb_client=dynamodb.meta.client,
        table_name=app_config.get_table_name(),
        gsi_name_query_by_sc_pa_id=app_config.get_gsi_name_query_by_alt_key(),
    )

    products_query_service = dynamodb_products_query_service.DynamoDBProductsQueryService(
        dynamodb_client=dynamodb.meta.client,
        table_name=app_config.get_table_name(),
    )

    pp_qry_srv = dynamodb_provisioned_products_query_service.DynamoDBProvisionedProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_primary_key(),
        gsi_custom_query_by_service_catalog_id=app_config.get_gsi_name_query_by_alt_key(),
        gsi_custom_query_by_user_id=app_config.get_gsi_name_query_by_user_key(),
        gsi_custom_query_all=app_config.get_gsi_name_query_by_alt_key_2(),
        gsi_custom_query_by_product_id=app_config.get_gsi_name_query_by_alt_keys_3(),
        gsi_custom_query_by_project_id=app_config.get_gsi_name_query_by_alt_keys_4(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_alt_keys_5(),
    )

    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=dynamodb,
        table_name=app_config.get_table_name(),
        logger=logger,
    ).register_migrations(migrations_config(provisioned_products_qs=pp_qry_srv)).migrate()

    publisher = aggregate.AggregatePublisher(
        mb=mb,
        uow=shared_uow,
    )

    aws_api_instance = aws_api.AWSAPI(
        api_url=app_config.get_publishing_api_url(),
        region=app_config.get_default_region(),
        logger=logger,
    )

    publishing_api_qs = publishing_api_query_service.PublishingApiQueryService(api=aws_api_instance, logger=logger)

    def _update_product_read_model_event_handler_factory():
        def _handle_event(
            product_read_model: product.Product,
        ):
            return update_product_read_model_event_handler.handle(
                product_obj=product_read_model,
                uow=shared_uow,
                versions_qry_srv=versions_query_service,
                publishing_qry_srv=publishing_api_qs,
            )

        return _handle_event

    def _update_recommended_version_read_model_event_handler_factory():
        def _handle_event(
            project_id: str,
            product_id: str,
            new_recommended_version_id: str,
        ):
            return update_recommended_version_handler.handle(
                project_id=project_id,
                product_id=product_id,
                new_recommended_version_id=new_recommended_version_id,
                versions_qry_srv=versions_query_service,
                product_qry_srv=products_query_service,
                uow=shared_uow,
            )

        return _handle_event

    def _check_for_upgrade_cmd_handler_factory():
        def _handle(
            command: check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand,
        ):
            check_if_upgrade_available.handle(
                command=command,
                publisher=publisher,
                logger=logger,
                pp_qry_srv=pp_qry_srv,
            )

        return _handle

    command_bus = command_bus_metrics.CommandBusMetrics(
        inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
        metrics_client=metrics_client,
    ).register_handler(
        check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand,
        _check_for_upgrade_cmd_handler_factory(),
    )

    return Dependencies(
        command_bus=command_bus,
        update_product_read_model_event_handler=_update_product_read_model_event_handler_factory(),
        update_recommended_version_read_model_event_handler=_update_recommended_version_read_model_event_handler_factory(),
    )
