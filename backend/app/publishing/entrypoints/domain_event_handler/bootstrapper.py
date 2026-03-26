import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.publishing.adapters.query_services import (
    dynamodb_products_query_service,
    dynamodb_shared_amis_query_service,
    dynamodb_versions_query_service,
    projects_api_query_service,
    service_catalog_query_service,
)
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.adapters.services import s3_file_service, service_catalog_service
from app.publishing.domain.command_handlers import (
    publish_version_command_handler,
    rename_version_distributions_command_handler,
    unpublish_product_command_handler,
    unpublish_version_command_handler,
    update_product_availability_command_handler,
)
from app.publishing.domain.commands import (
    publish_version_command,
    rename_version_distributions_command,
    unpublish_product_command,
    unpublish_version_command,
    update_product_availability_command,
)
from app.publishing.domain.query_services import (
    template_domain_query_service,
)
from app.publishing.entrypoints.domain_event_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
from app.shared.api import aws_api, aws_events_api
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus

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

    versions_qry_srv = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    aws_api_instance = aws_api.AWSAPI(
        api_url=app_config.get_projects_api_url(),
        region=app_config.get_default_region(),
        logger=logger,
    )

    projects_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=aws_api_instance)

    file_service = s3_file_service.S3FileService(
        admin_role=app_config.get_admin_role(),
        tools_aws_account_id=app_config.get_tools_aws_account_id(),
        region=app_config.get_default_region(),
        bucket_name=app_config.get_templates_s3_bucket_name(),
        logger=logger,
        boto_session=session,
    )

    shared_amis_qry_svc = dynamodb_shared_amis_query_service.DynamoDBSharedAMIsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    products_qry_srv = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    template_domain_qry_srv = template_domain_query_service.TemplateDomainQueryService(
        workbench_template=app_config.get_workbench_template_file_path(),
        virtual_target_template=app_config.get_virtual_target_template_file_path(),
        container_template=app_config.get_container_template_file_path(),
        products_qry_srv=products_qry_srv,
        template_srv=file_service,
        versions_qry_srv=versions_qry_srv,
    )

    def _publish_version_cmd_handler_factory():
        def _handle_command(command: publish_version_command.PublishVersionCommand):
            return publish_version_command_handler.handle(
                cmd=command,
                uow=shared_uow,
                catalog_qry_srv=sc_qry_service,
                catalog_srv=sc_service,
                logger=logger,
                msg_bus=message_bus,
                projects_qry_srv=projects_api_qry_srv,
                file_srv=file_service,
                shared_amis_qry_srv=shared_amis_qry_svc,
                template_qry_srv=template_domain_qry_srv,
            )

        return _handle_command

    def _rename_version_distributions_cmd_handler_factory():
        def _handle_command(
            command: rename_version_distributions_command.RenameVersionDistributionsCommand,
        ):
            return rename_version_distributions_command_handler.handle(
                command=command, uow=shared_uow, catalog_srv=sc_service, logger=logger
            )

        return _handle_command

    def _unpublish_product_cmd_handler_factory():
        def _handle_command(command: unpublish_product_command.UnpublishProductCommand):
            return unpublish_product_command_handler.handle(
                cmd=command,
                uow=shared_uow,
                versions_qry_srv=versions_qry_srv,
                catalog_qry_srv=sc_qry_service,
                catalog_srv=sc_service,
                logger=logger,
                msg_bus=message_bus,
            )

        return _handle_command

    def _unpublish_version_cmd_handler_factory():
        def _handle_command(command: unpublish_version_command.UnpublishVersionCommand):
            return unpublish_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                catalog_srv=sc_service,
                catalog_qry_srv=sc_qry_service,
                logger=logger,
                msg_bus=message_bus,
            )

        return _handle_command

    def _update_product_availability_cmd_handler_factory():
        def _handle_command(
            command: update_product_availability_command.UpdateProductAvailabilityCommand,
        ):
            return update_product_availability_command_handler.handle(
                command=command,
                uow=shared_uow,
                versions_qry_srv=versions_qry_srv,
                logger=logger,
                message_bus=message_bus,
            )

        return _handle_command

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            publish_version_command.PublishVersionCommand,
            _publish_version_cmd_handler_factory(),
        )
        .register_handler(
            rename_version_distributions_command.RenameVersionDistributionsCommand,
            _rename_version_distributions_cmd_handler_factory(),
        )
        .register_handler(
            unpublish_product_command.UnpublishProductCommand,
            _unpublish_product_cmd_handler_factory(),
        )
        .register_handler(
            unpublish_version_command.UnpublishVersionCommand,
            _unpublish_version_cmd_handler_factory(),
        )
        .register_handler(
            update_product_availability_command.UpdateProductAvailabilityCommand,
            _update_product_availability_cmd_handler_factory(),
        )
    )

    return Dependencies(command_bus=command_bus)
