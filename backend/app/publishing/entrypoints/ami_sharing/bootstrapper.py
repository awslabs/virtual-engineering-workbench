import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel, ConfigDict

from app.publishing.adapters.query_services import (
    dynamodb_amis_query_service,
    dynamodb_shared_amis_query_service,
    projects_api_query_service,
)
from app.publishing.adapters.repository import dynamo_entity_config
from app.publishing.adapters.services import ec2_image_service
from app.publishing.adapters.services.aws_license_manager_service import AwsLicenseManagerService
from app.publishing.domain.command_handlers import (
    accept_license_grant_command_handler,
    copy_ami_command_handler,
    create_license_grant_command_handler,
    fail_ami_sharing_command_handler,
    share_ami_command_handler,
    succeed_ami_sharing_command_handler,
)
from app.publishing.domain.commands import (
    accept_license_grant_command,
    copy_ami_command,
    create_license_grant_command,
    fail_ami_sharing_command,
    share_ami_command,
    succeed_ami_sharing_command,
)
from app.publishing.domain.ports.license_manager_service import LicenseManagerService
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
from app.shared.api import aws_events_api, bounded_contexts, service_registry
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    shared_amis_domain_qry_svc: shared_amis_domain_query_service.SharedAMIsDomainQueryService
    license_manager_svc: LicenseManagerService
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

    ec2_img_srv = ec2_image_service.EC2ImageService(
        image_srv_role=app_config.get_image_service_role(),
        image_srv_aws_account_id=app_config.get_image_service_aws_account_id(),
        image_srv_key_name=app_config.get_image_service_key_name(),
        image_srv_region=app_config.get_default_region(),
        boto_session=session,
    )

    license_manager_svc = AwsLicenseManagerService(
        spoke_account_role=app_config.get_spoke_account_role(),
        region=app_config.get_default_region(),
        boto_session=session,
    )

    amis_qry_svc = dynamodb_amis_query_service.DynamoDBAMIsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
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

    # Cross-BC read used to authorize a licence grant: the AMI must belong to the
    # project and the target account must be one of its active accounts.
    projects_aws_api = service_registry.ServiceRegistry.from_config(
        app_config=app_config,
        ssm_client=boto3.client("ssm", region_name=app_config.get_default_region()),
        logger=logger,
    ).api_for(bounded_contexts.BoundedContext.PROJECTS)
    projects_api_qry_srv = projects_api_query_service.ProjectsApiQueryService(api=projects_aws_api)

    def _create_license_grant_cmd_handler_factory():
        def _handle_command(command: create_license_grant_command.CreateLicenseGrantCommand):
            return create_license_grant_command_handler.handle(
                command=command,
                uow=shared_uow,
                license_manager_service=license_manager_svc,
                msg_bus=message_bus,
                amis_query_service=amis_qry_svc,
                projects_query_service=projects_api_qry_srv,
                logger=logger,
            )

        return _handle_command

    def _accept_license_grant_cmd_handler_factory():
        def _handle_command(command: accept_license_grant_command.AcceptLicenseGrantCommand):
            return accept_license_grant_command_handler.handle(
                command=command,
                uow=shared_uow,
                license_manager_service=license_manager_svc,
                msg_bus=message_bus,
                logger=logger,
            )

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
        .register_handler(
            create_license_grant_command.CreateLicenseGrantCommand, _create_license_grant_cmd_handler_factory()
        )
        .register_handler(
            accept_license_grant_command.AcceptLicenseGrantCommand, _accept_license_grant_cmd_handler_factory()
        )
    )

    shared_amis_qry_svc = dynamodb_shared_amis_query_service.DynamoDBSharedAMIsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )
    shared_amis_domain_qry_svc = shared_amis_domain_query_service.SharedAMIsDomainQueryService(
        unit_of_work=shared_uow,
        image_svc=ec2_img_srv,
        shared_amis_qry_svc=shared_amis_qry_svc,
        default_original_ami_region=app_config.get_default_region(),
        license_manager_svc=license_manager_svc,
    )
    return Dependencies(
        command_bus=command_bus,
        shared_amis_domain_qry_svc=shared_amis_domain_qry_svc,
        license_manager_svc=license_manager_svc,
    )
