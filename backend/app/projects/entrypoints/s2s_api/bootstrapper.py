from typing import Optional

import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.projects.adapters.query_services import dynamodb_query_service
from app.projects.adapters.repository import dynamo_entity_config
from app.projects.adapters.repository.dynamo_entity_migrations import migrations_config
from app.projects.domain.command_handlers.enrolments import (
    approve_enrolments_command_handler,
    enrol_user_to_program_command_handler,
)
from app.projects.domain.command_handlers.users import (
    assign_user_command_handler,
    reassign_user_command_handler,
    unassign_user_command_handler,
)
from app.projects.domain.commands.enrolments import approve_enrolments_command, enrol_user_to_program_command
from app.projects.domain.commands.users import assign_user_command, reassign_user_command, unassign_user_command
from app.projects.domain.ports import enrolment_query_service, projects_query_service, technologies_query_service
from app.projects.entrypoints.s2s_api import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_migrations
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work as dynamodb_unit_of_work_v2
from app.shared.api import aws_events_api
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    projects_query_service: projects_query_service.ProjectsQueryService
    technologies_query_service: technologies_query_service.TechnologiesQueryService
    enrolment_query_service: enrolment_query_service.EnrolmentQueryService

    class Config:
        arbitrary_types_allowed = True


def bootstrap(
    app_config: config.AppConfig,
    logger: logging.Logger,
    projects_query_service: Optional[projects_query_service.ProjectsQueryService] = None,
) -> Dependencies:
    session = boto_logger.loggable_session(boto3.session.Session(), logger)

    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())

    dynamodb_migrations.DynamoDBMigrator(
        ddb_resource=dynamodb,
        table_name=app_config.get_table_name(),
        logger=logger,
    ).register_migrations(migrations_config(gsi_entities=app_config.get_entities_gsi_name())).migrate()

    enrolment_qry_srv = dynamodb_query_service.DynamoDBEnrolmentQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_qpk=app_config.get_entities_gsi_name_qpk(),
        gsi_qsk=app_config.get_gsi_name_qsk(),
    )

    shared_uow_v2 = dynamodb_unit_of_work_v2.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

    projects_query_service = dynamodb_query_service.DynamoDBProjectsQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_inverted_primary_key_gsi_name(),
        gsi_aws_accounts=app_config.get_aws_accounts_gsi_name(),
        gsi_entities=app_config.get_entities_gsi_name(),
    )

    technologies_qry_srv = dynamodb_query_service.DynamoDBTechnologiesQueryService(
        table_name=app_config.get_table_name(), dynamodb_client=dynamodb.meta.client
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

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger), metrics_client=metrics_client
        )
        .register_handler(
            approve_enrolments_command.ApproveEnrolmentsCommand,
            lambda command: approve_enrolments_command_handler.handle_approve_enrolments_command(
                cmd=command,
                uow=shared_uow_v2,
                enrolment_qry_srv=enrolment_qry_srv,
                project_qry_srv=projects_query_service,
                message_bus=message_bus,
            ),
        )
        .register_handler(
            enrol_user_to_program_command.EnrolUserToProgramCommand,
            lambda command: enrol_user_to_program_command_handler.handle_enrol_user_to_program_command(
                cmd=command,
                uow=shared_uow_v2,
                projects_qry_srv=projects_query_service,
                enrolment_qry_srv=enrolment_qry_srv,
                msg_bus=message_bus,
            ),
        )
        .register_handler(
            assign_user_command.AssignUserCommand,
            lambda command: assign_user_command_handler.handle_assign_user_command(
                cmd=command,
                unit_of_work=shared_uow_v2,
                projects_query_service=projects_query_service,
                message_bus=message_bus,
            ),
        )
        .register_handler(
            unassign_user_command.UnAssignUserCommand,
            lambda command: unassign_user_command_handler.handle_unassign_user_command(
                cmd=command,
                uow=shared_uow_v2,
                projects_qry_service=projects_query_service,
                msg_bus=message_bus,
                enrolment_qry_service=enrolment_qry_srv,
            ),
        )
        .register_handler(
            reassign_user_command.ReAssignUserCommand,
            lambda command: reassign_user_command_handler.handle_reassign_user_command(
                cmd=command,
                unit_of_work=shared_uow_v2,
                projects_query_service=projects_query_service,
                message_bus=message_bus,
            ),
        )
    )

    return Dependencies(
        command_bus=command_bus,
        projects_query_service=projects_query_service,
        technologies_query_service=technologies_qry_srv,
        enrolment_query_service=enrolment_qry_srv,
    )
