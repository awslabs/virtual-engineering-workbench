from typing import Callable

import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel, ConfigDict

from app.publishing.adapters.query_services import (
    dynamodb_portfolios_query_service,
    dynamodb_products_query_service,
    dynamodb_versions_query_service,
)
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.adapters.services import cloud_formation_service, s3_file_service
from app.publishing.domain.event_handlers import (
    create_automated_version_event_handler,
    delete_ami_read_model_event_handler,
    update_ami_read_model_event_handler,
)
from app.publishing.domain.query_services import template_domain_query_service
from app.publishing.domain.read_models import ami
from app.publishing.domain.value_objects import ami_id_value_object
from app.publishing.entrypoints.packaging_event_handler import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work
from app.shared.api import aws_events_api, ssm_parameter_service
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    update_ami_read_model_event_handler: Callable
    delete_ami_read_model_event_handler: Callable
    create_automated_version_event_handler: Callable
    model_config = ConfigDict(arbitrary_types_allowed=True)


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

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    events_client = session.client("events", region_name=app_config.get_default_region())
    events_api = aws_events_api.AWSEventsApi(client=events_client)

    message_bus = event_bridge_message_bus.EventBridgeMessageBus(
        events_api=events_api,
        event_bus_name=app_config.get_domain_event_bus_name(),
        bounded_context_name=app_config.get_bounded_context_name(),
        logger=logger,
    )

    command_bus = command_bus_metrics.CommandBusMetrics(
        inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
        metrics_client=metrics_client,
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

    products_qry_srv = dynamodb_products_query_service.DynamoDBProductsQueryService(
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

    file_service = s3_file_service.S3FileService(
        admin_role=app_config.get_admin_role(),
        tools_aws_account_id=app_config.get_tools_aws_account_id(),
        region=app_config.get_default_region(),
        bucket_name=app_config.get_templates_s3_bucket_name(),
        logger=logger,
        boto_session=session,
    )

    template_domain_qry_srv = template_domain_query_service.TemplateDomainQueryService(
        workbench_template=app_config.get_workbench_template_file_path(),
        virtual_target_template=app_config.get_virtual_target_template_file_path(),
        container_template=app_config.get_container_template_file_path(),
        products_qry_srv=products_qry_srv,
        template_srv=file_service,
        versions_qry_srv=versions_qry_srv,
    )

    ssm_api_instance = ssm_parameter_service.SSMApi(region=app_config.get_default_region(), session=session)

    def _update_ami_read_model_event_handler_factory():
        def _handle_event(new_ami: ami.Ami, retired_ami_ids: list[str]):
            return update_ami_read_model_event_handler.handle(
                new_ami=new_ami,
                retired_ami_ids=retired_ami_ids,
                uow=shared_uow,
                logger=logger,
            )

        return _handle_event

    def _delete_ami_read_model_event_handler_factory():
        def _handle_event(ami_id: ami_id_value_object.AmiIdValueObject):
            return delete_ami_read_model_event_handler.handle(ami_id=ami_id, logger=logger, uow=shared_uow)

        return _handle_event

    def _create_automated_version_event_handler_factory():
        def _handle_event(
            ami_id: str,
            product_id: str,
            project_id: str,
            release_type: str,
            user_id: str,
            component_version_details: list,
            os_version: str,
            platform: str,
            architecture: str,
            integrations: list,
        ):
            return create_automated_version_event_handler.handle(
                ami_id=ami_id,
                product_id=product_id,
                project_id=project_id,
                release_type=release_type,
                user_id=user_id,
                component_version_details=component_version_details,
                os_version=os_version,
                platform=platform,
                architecture=architecture,
                integrations=integrations,
                template_domain_qry_srv=template_domain_qry_srv,
                logger=logger,
                uow=shared_uow,
                message_bus=message_bus,
                portf_qry_srv=portfolios_qry_srv,
                version_qry_srv=versions_qry_srv,
                param_service=ssm_api_instance,
                product_version_limit_param_name=app_config.get_product_version_limit_param_name(),
                product_rc_version_limit_param_name=app_config.get_product_rc_version_limit_param_name(),
                stack_srv=stack_service,
                file_service=file_service,
            )

        return _handle_event

    return Dependencies(
        command_bus=command_bus,
        update_ami_read_model_event_handler=_update_ami_read_model_event_handler_factory(),
        delete_ami_read_model_event_handler=_delete_ami_read_model_event_handler_factory(),
        create_automated_version_event_handler=_create_automated_version_event_handler_factory(),
    )
