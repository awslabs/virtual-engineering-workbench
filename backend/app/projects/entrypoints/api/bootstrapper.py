from typing import Optional

import boto3
from aws_lambda_powertools import logging
from pydantic import BaseModel, ConfigDict

from app.projects.adapters.query_services import dynamodb_query_service
from app.projects.adapters.repository import dynamo_entity_config
from app.projects.adapters.repository.dynamo_entity_migrations import migrations_config
from app.projects.adapters.services import cognito_user_directory_service
from app.projects.domain.command_handlers.enrolments import (
    approve_enrolments_command_handler,
    enrol_user_to_program_command_handler,
    reject_enrolments_command_handler,
)
from app.projects.domain.command_handlers.project_accounts import (
    activate_project_account_command_handler,
    deactivate_project_account_command_handler,
    on_board_project_account_command_handler,
    reonboard_project_account_command_handler,
)
from app.projects.domain.command_handlers.projects import (
    create_project_command_handler,
    update_project_command_handler,
)
from app.projects.domain.command_handlers.technologies import (
    add_technology_command_handler,
    delete_technology_command_handler,
    update_technology_command_handler,
)
from app.projects.domain.command_handlers.users import (
    assign_user_command_handler,
    reassign_user_command_handler,
    unassign_user_command_handler,
)
from app.projects.domain.commands.enrolments import (
    approve_enrolments_command,
    enrol_user_to_program_command,
    reject_enrolments_command,
)
from app.projects.domain.commands.project_accounts import (
    activate_project_account_command,
    deactivate_project_account_command,
    on_board_project_account_command,
    reonboard_project_account_command,
)
from app.projects.domain.commands.projects import (
    create_project_command,
    update_project_command,
)
from app.projects.domain.commands.technologies import (
    add_technology,
    delete_technology_command,
    update_technology_command,
)
from app.projects.domain.commands.users import (
    assign_user_command,
    reassign_user_command,
    unassign_user_command,
)
from app.projects.domain.ports import (
    enrolment_query_service,
    projects_query_service,
    technologies_query_service,
)
from app.projects.entrypoints.api import config
from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    event_bridge_message_bus,
    in_memory_command_bus,
    message_bus_metrics,
)
from app.shared.adapters.unit_of_work_v2 import (
    dynamodb_migrations,
)
from app.shared.adapters.unit_of_work_v2 import dynamodb_unit_of_work as dynamodb_unit_of_work_v2
from app.shared.api import aws_events_api
from app.shared.instrumentation import power_tools_metrics
from app.shared.logging import boto_logger


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus
    projects_query_service: projects_query_service.ProjectsQueryService
    technologies_query_service: technologies_query_service.TechnologiesQueryService
    enrolment_query_service: enrolment_query_service.EnrolmentQueryService
    model_config = ConfigDict(arbitrary_types_allowed=True)


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

    cognito_idp_client = session.client("cognito-idp", region_name=app_config.get_default_region())
    user_directory_svc = cognito_user_directory_service.CognitoUserDirectoryService(
        cognito_client=cognito_idp_client,
        user_pool_id=app_config.get_cognito_user_pool_id(),
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

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            on_board_project_account_command.OnBoardProjectAccountCommand,
            lambda command: on_board_project_account_command_handler.handle_on_board_project_account_command(
                command=command,
                unit_of_work=shared_uow_v2,
                projects_query_service=projects_query_service,
                message_bus=message_bus,
                web_application_account_id=app_config.get_web_application_account_id(),
                web_application_environment=app_config.get_web_application_environment(),
                web_application_region=app_config.get_default_region(),
                image_service_account_id=app_config.get_image_service_account_id(),
                catalog_service_account_id=app_config.get_catalog_service_account_id(),
            ),
        )
        .register_handler(
            reonboard_project_account_command.ReonboardProjectAccountCommand,
            lambda command: reonboard_project_account_command_handler.handle(
                command=command,
                unit_of_work=shared_uow_v2,
                projects_query_service=projects_query_service,
                message_bus=message_bus,
                web_application_account_id=app_config.get_web_application_account_id(),
                web_application_environment=app_config.get_web_application_environment(),
                web_application_region=app_config.get_default_region(),
                image_service_account_id=app_config.get_image_service_account_id(),
                catalog_service_account_id=app_config.get_catalog_service_account_id(),
            ),
        )
        .register_handler(
            assign_user_command.AssignUserCommand,
            lambda command: assign_user_command_handler.handle_assign_user_command(
                cmd=command,
                unit_of_work=shared_uow_v2,
                projects_query_service=projects_query_service,
                message_bus=message_bus,
                user_directory_service=user_directory_svc,
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
            add_technology.AddTechnologyCommand,
            lambda command: add_technology_command_handler.handle_add_technology_command(
                cmd=command,
                uow=shared_uow_v2,
                projects_qry_srv=projects_query_service,
                msg_bus=message_bus,
            ),
        )
        .register_handler(
            update_technology_command.UpdateTechnologyCommand,
            lambda command: update_technology_command_handler.handle_update_technology_command(
                cmd=command,
                uow=shared_uow_v2,
                projects_qry_srv=projects_query_service,
                technologies_qry_srv=technologies_qry_srv,
                msg_bus=message_bus,
            ),
        )
        .register_handler(
            delete_technology_command.DeleteTechnologyCommand,
            lambda command: delete_technology_command_handler.handle_delete_technology_command(
                cmd=command,
                uow=shared_uow_v2,
                projects_qry_srv=projects_query_service,
                msg_bus=message_bus,
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
            reject_enrolments_command.RejectEnrolmentsCommand,
            lambda command: reject_enrolments_command_handler.handle_reject_enrolments_command(
                cmd=command,
                uow=shared_uow_v2,
                enrolment_qry_srv=enrolment_qry_srv,
                project_qry_srv=projects_query_service,
                message_bus=message_bus,
            ),
        )
        .register_handler(
            activate_project_account_command.ActivateProjectAccountCommand,
            lambda command: activate_project_account_command_handler.handle_activate_project_account_command(
                cmd=command,
                unit_of_work=shared_uow_v2,
                projects_qry_srv=projects_query_service,
            ),
        )
        .register_handler(
            deactivate_project_account_command.DeactivateProjectAccountCommand,
            lambda command: deactivate_project_account_command_handler.handle_deactivate_project_account_command(
                cmd=command,
                unit_of_work=shared_uow_v2,
                projects_qry_srv=projects_query_service,
            ),
        )
        .register_handler(
            create_project_command.CreateProjectCommand,
            lambda command: create_project_command_handler.handle_create_project_command(
                cmd=command, uow=shared_uow_v2, msg_bus=message_bus
            ),
        )
        .register_handler(
            update_project_command.UpdateProjectCommand,
            lambda command: update_project_command_handler.handle_update_project_command(
                cmd=command, uow=shared_uow_v2, msg_bus=message_bus
            ),
        )
    )

    return Dependencies(
        command_bus=command_bus,
        projects_query_service=projects_query_service,
        technologies_query_service=technologies_qry_srv,
        enrolment_query_service=enrolment_qry_srv,
    )
