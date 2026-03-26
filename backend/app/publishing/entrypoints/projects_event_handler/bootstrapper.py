import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.publishing.adapters.query_services import service_catalog_query_service
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.adapters.services import service_catalog_service
from app.publishing.domain.command_handlers import (
    create_portfolio_command_handler,
)
from app.publishing.domain.commands import (
    create_portfolio_command,
)
from app.publishing.entrypoints.projects_event_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    in_memory_command_bus,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
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

    shared_uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )
    sc_service = service_catalog_service.ServiceCatalogService(
        admin_role=app_config.get_admin_role(),
        use_case_role=app_config.get_use_case_role(),
        launch_constraint_role=app_config.get_launch_constraint_role(),
        notification_constraint_topic_arn_resolver=app_config.get_notification_arn_for_region,
        tools_aws_account_id=app_config.get_tools_aws_account_id(),
        bucket_name=app_config.get_templates_s3_bucket_name(),
        boto_session=session,
        resource_update_constraint_allowed=app_config.get_resource_update_constraint_allowed_value(),
    )

    sc_qry_service = service_catalog_query_service.ServiceCatalogQueryService(
        admin_role=app_config.get_admin_role(),
        use_case_role=app_config.get_use_case_role(),
        technical_parameters_names=app_config.get_technical_parameters_names(),
        tools_aws_account_id=app_config.get_tools_aws_account_id(),
        logger=logger,
        boto_session=session,
    )

    def _create_portfolio_handler_factory():
        def _handle_command(
            command: create_portfolio_command.CreatePortfolioCommand,
        ):
            return create_portfolio_command_handler.handle(
                cmd=command,
                uow=shared_uow,
                catalog_qry_srv=sc_qry_service,
                catalog_srv=sc_service,
                logger=logger,
                main_account_roles={app_config.get_admin_role()},
                spoke_account_roles={app_config.get_provisioning_role()},
            )

        return _handle_command

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    command_bus = command_bus_metrics.CommandBusMetrics(
        inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
        metrics_client=metrics_client,
    ).register_handler(
        create_portfolio_command.CreatePortfolioCommand,
        _create_portfolio_handler_factory(),
    )

    return Dependencies(
        command_bus=command_bus,
    )
