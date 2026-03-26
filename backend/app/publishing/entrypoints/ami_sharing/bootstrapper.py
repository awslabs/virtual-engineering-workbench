import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.adapters.services import ec2_image_service
from app.publishing.domain.command_handlers import (
    copy_ami_command_handler,
    fail_ami_sharing_command_handler,
    share_ami_command_handler,
    succeed_ami_sharing_command_handler,
)
from app.publishing.domain.commands import (
    copy_ami_command,
    fail_ami_sharing_command,
    share_ami_command,
    succeed_ami_sharing_command,
)
from app.publishing.domain.query_services import shared_amis_domain_query_service
from app.publishing.entrypoints.ami_sharing import config
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


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    shared_amis_domain_qry_svc: shared_amis_domain_query_service.SharedAMIsDomainQueryService

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

    ec2_img_srv = ec2_image_service.EC2ImageService(
        image_srv_role=app_config.get_image_service_role(),
        image_srv_aws_account_id=app_config.get_image_service_aws_account_id(),
        image_srv_key_name=app_config.get_image_service_key_name(),
        image_srv_region=app_config.get_default_region(),
        boto_session=session,
    )

    def _copy_ami_cmd_handler_factory():
        def _handle_command(command: copy_ami_command.CopyAmiCommand):
            return copy_ami_command_handler.handle(cmd=command, uow=shared_uow, img_srv=ec2_img_srv, logger=logger)

        return _handle_command

    def _share_ami_cmd_handler_factory():
        def _handle_command(command: share_ami_command.ShareAmiCommand):
            return share_ami_command_handler.handle(cmd=command, uow=shared_uow, img_srv=ec2_img_srv, logger=logger)

        return _handle_command

    def _succeed_ami_sharing_cmd_handler_factory():
        def _handle_command(command: succeed_ami_sharing_command.SucceedAmiSharingCommand):
            return succeed_ami_sharing_command_handler.handle(
                cmd=command, uow=shared_uow, msg_bus=message_bus, logger=logger
            )

        return _handle_command

    def _fail_ami_sharing_cmd_handler_factory():
        def _handle_command(command: fail_ami_sharing_command.FailAmiSharingCommand):
            return fail_ami_sharing_command_handler.handle(cmd=command, uow=shared_uow, logger=logger)

        return _handle_command

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger), metrics_client=metrics_client
        )
        .register_handler(copy_ami_command.CopyAmiCommand, _copy_ami_cmd_handler_factory())
        .register_handler(share_ami_command.ShareAmiCommand, _share_ami_cmd_handler_factory())
        .register_handler(
            succeed_ami_sharing_command.SucceedAmiSharingCommand, _succeed_ami_sharing_cmd_handler_factory()
        )
        .register_handler(fail_ami_sharing_command.FailAmiSharingCommand, _fail_ami_sharing_cmd_handler_factory())
    )

    shared_amis_domain_qry_svc = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=shared_uow, image_svc=ec2_img_srv, default_original_ami_region=app_config.get_default_region()
    )
    return Dependencies(
        command_bus=command_bus,
        shared_amis_domain_qry_svc=shared_amis_domain_qry_svc,
    )
