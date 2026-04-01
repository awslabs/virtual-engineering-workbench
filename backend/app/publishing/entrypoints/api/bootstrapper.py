import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel, ConfigDict

from app.publishing.adapters.query_services import (
    dynamodb_amis_query_service,
    dynamodb_portfolios_query_service,
    dynamodb_products_query_service,
    dynamodb_versions_query_service,
)
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.adapters.services import cloud_formation_service, s3_file_service
from app.publishing.domain.command_handlers import (
    archive_product_command_handler,
    create_product_command_handler,
    create_version_command_handler,
    promote_version_command_handler,
    restore_version_command_handler,
    retire_version_command_handler,
    retry_version_command_handler,
    set_recommended_version_command_handler,
    update_version_command_handler,
    validate_version_command_handler,
)
from app.publishing.domain.commands import (
    archive_product_command,
    create_product_command,
    create_version_command,
    promote_version_command,
    restore_version_command,
    retire_version_command,
    retry_version_command,
    set_recommended_version_command,
    update_version_command,
    validate_version_command,
)
from app.publishing.domain.query_services import (
    amis_domain_query_service,
    portfolios_domain_query_service,
    products_domain_query_service,
    template_domain_query_service,
    versions_domain_query_service,
)
from app.publishing.entrypoints.api import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
from app.shared.api import aws_events_api, ssm_parameter_service
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    products_domain_qry_srv: products_domain_query_service.ProductsDomainQueryService
    amis_domain_qry_srv: amis_domain_query_service.AMIsDomainQueryService
    versions_domain_qry_srv: versions_domain_query_service.VersionsDomainQueryService
    portfolios_domain_qry_srv: portfolios_domain_query_service.PortfoliosDomainQueryService
    template_domain_qry_srv: template_domain_query_service.TemplateDomainQueryService
    model_config = ConfigDict(arbitrary_types_allowed=True)


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

    portfolios_qry_srv = dynamodb_portfolios_query_service.DynamoDBPortfoliosQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )
    versions_qry_srv = dynamodb_versions_query_service.DynamoDBVersionsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    stack_service = cloud_formation_service.CloudFormationService(
        admin_role=app_config.get_admin_role(),
        tools_aws_account_id=app_config.get_tools_aws_account_id(),
        region=app_config.get_default_region(),
        boto_session=session,
    )

    ssm_api_instance = ssm_parameter_service.SSMApi(region=app_config.get_default_region(), session=session)

    products_qry_srv = dynamodb_products_query_service.DynamoDBProductsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    products_domain_qry_srv = products_domain_query_service.ProductsDomainQueryService(
        products_qry_srv=products_qry_srv,
        versions_qry_srv=versions_qry_srv,
    )

    file_service = s3_file_service.S3FileService(
        admin_role=app_config.get_admin_role(),
        tools_aws_account_id=app_config.get_tools_aws_account_id(),
        region=app_config.get_default_region(),
        bucket_name=app_config.get_templates_s3_bucket_name(),
        logger=logger,
        boto_session=session,
    )

    versions_domain_qry_srv = versions_domain_query_service.VersionsDomainQueryService(
        version_qry_srv=versions_qry_srv,
        file_srv=file_service,
        default_original_ami_region=app_config.get_default_region(),
    )

    portfolios_domain_qry_srv = portfolios_domain_query_service.PortfoliosDomainQueryService(
        portfolio_qry_srv=portfolios_qry_srv
    )

    amis_qry_srv = dynamodb_amis_query_service.DynamoDBAMIsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    amis_domain_qry_srv = amis_domain_query_service.AMIsDomainQueryService(
        ami_qry_srv=amis_qry_srv,
        template_srv=file_service,
        used_ami_list_file_path=app_config.get_used_ami_list_file_path(),
    )

    template_domain_qry_srv = template_domain_query_service.TemplateDomainQueryService(
        workbench_template=app_config.get_workbench_template_file_path(),
        virtual_target_template=app_config.get_virtual_target_template_file_path(),
        container_template=app_config.get_container_template_file_path(),
        products_qry_srv=products_qry_srv,
        template_srv=file_service,
        versions_qry_srv=versions_qry_srv,
    )

    def _create_product_command_handler_factory():
        def _handle_command(
            command: create_product_command.CreateProductCommand,
        ):
            return create_product_command_handler.handle(
                command=command,
                unit_of_work=shared_uow,
                message_bus=message_bus,
            )

        return _handle_command

    def _archive_product_command_handler_factory():
        def _handle_command(command: archive_product_command.ArchiveProductCommand):
            return archive_product_command_handler.handle(
                cmd=command,
                uow=shared_uow,
                message_bus=message_bus,
            )

        return _handle_command

    def _create_version_command_handler_factory():
        def _handle_command(command: create_version_command.CreateVersionCommand):
            return create_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                portf_qry_srv=portfolios_qry_srv,
                version_qry_srv=versions_qry_srv,
                param_service=ssm_api_instance,
                product_version_limit_param_name=app_config.get_product_version_limit_param_name(),
                product_rc_version_limit_param_name=app_config.get_product_rc_version_limit_param_name(),
                stack_srv=stack_service,
                amis_qry_srv=amis_qry_srv,
                file_service=file_service,
                template_query_service=template_domain_qry_srv,
            )

        return _handle_command

    def _validate_version_command_handler_factory():
        def _handle_command(command: validate_version_command.ValidateVersionCommand):
            return validate_version_command_handler.handle(
                command=command,
                stack_srv=stack_service,
            )

        return _handle_command

    def _update_version_command_handler_factory():
        def _handle_command(command: update_version_command.UpdateVersionCommand):
            return update_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                version_qry_srv=versions_qry_srv,
                stack_srv=stack_service,
                amis_qry_srv=amis_qry_srv,
                file_service=file_service,
                template_query_service=template_domain_qry_srv,
            )

        return _handle_command

    def _retry_version_command_handler_factory():
        def _handle_command(command: retry_version_command.RetryVersionCommand):
            return retry_version_command_handler.handle(
                cmd=command,
                uow=shared_uow,
                versions_qry_srv=versions_qry_srv,
                message_bus=message_bus,
                product_qry_srv=products_qry_srv,
            )

        return _handle_command

    def _promote_version_command_handler_factory():
        def _handle_command(command: promote_version_command.PromoteVersionCommand):
            return promote_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                portf_qry_srv=portfolios_qry_srv,
                versions_qry_srv=versions_qry_srv,
                amis_qry_srv=amis_qry_srv,
            )

        return _handle_command

    def _restore_version_command_handler_factory():
        def _handle_command(command: restore_version_command.RestoreVersionCommand):
            return restore_version_command_handler.handle(
                cmd=command,
                uow=shared_uow,
                msg_bus=message_bus,
                portfolios_qry_srv=portfolios_qry_srv,
                versions_qry_srv=versions_qry_srv,
                param_service=ssm_api_instance,
                product_version_limit_param_name=app_config.get_product_version_limit_param_name(),
                file_service=file_service,
                template_query_service=template_domain_qry_srv,
            )

        return _handle_command

    def _retire_version_command_handler_factory():
        def _handle_command(command: retire_version_command.RetireVersionCommand):
            return retire_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                versions_qry_srv=versions_qry_srv,
            )

        return _handle_command

    def _set_recommended_version_command_handler_factory():
        def _handle_command(
            command: set_recommended_version_command.SetRecommendedVersionCommand,
        ):
            return set_recommended_version_command_handler.handle(
                cmd=command,
                uow=shared_uow,
                msg_bus=message_bus,
                versions_qry_srv=versions_qry_srv,
                products_query_service=products_qry_srv,
            )

        return _handle_command

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            create_product_command.CreateProductCommand,
            _create_product_command_handler_factory(),
        )
        .register_handler(
            create_version_command.CreateVersionCommand,
            _create_version_command_handler_factory(),
        )
        .register_handler(
            validate_version_command.ValidateVersionCommand,
            _validate_version_command_handler_factory(),
        )
        .register_handler(
            update_version_command.UpdateVersionCommand,
            _update_version_command_handler_factory(),
        )
        .register_handler(
            retry_version_command.RetryVersionCommand,
            _retry_version_command_handler_factory(),
        )
        .register_handler(
            promote_version_command.PromoteVersionCommand,
            _promote_version_command_handler_factory(),
        )
        .register_handler(
            restore_version_command.RestoreVersionCommand,
            _restore_version_command_handler_factory(),
        )
        .register_handler(
            retire_version_command.RetireVersionCommand,
            _retire_version_command_handler_factory(),
        )
        .register_handler(
            archive_product_command.ArchiveProductCommand,
            _archive_product_command_handler_factory(),
        )
        .register_handler(
            set_recommended_version_command.SetRecommendedVersionCommand,
            _set_recommended_version_command_handler_factory(),
        )
    )

    return Dependencies(
        command_bus=command_bus,
        products_domain_qry_srv=products_domain_qry_srv,
        amis_domain_qry_srv=amis_domain_qry_srv,
        versions_domain_qry_srv=versions_domain_qry_srv,
        portfolios_domain_qry_srv=portfolios_domain_qry_srv,
        template_domain_qry_srv=template_domain_qry_srv,
    )
