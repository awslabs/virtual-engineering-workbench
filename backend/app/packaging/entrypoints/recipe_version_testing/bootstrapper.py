import json

import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from pydantic import BaseModel, ConfigDict

from app.packaging.adapters.query_services import (
    dynamodb_component_version_query_service,
    dynamodb_recipe_query_service,
    dynamodb_recipe_version_query_service,
    dynamodb_recipe_version_test_execution_query_service,
)
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.services import aws_recipe_version_testing_service
from app.packaging.domain.command_handlers.recipe import (
    check_recipe_version_testing_environment_launch_status_command_handler,
    check_recipe_version_testing_environment_setup_status_command_handler,
    check_recipe_version_testing_test_status_command_handler,
    complete_recipe_version_testing_command_handler,
    launch_recipe_version_testing_environment_command_handler,
    run_recipe_version_testing_command_handler,
    setup_recipe_version_testing_environment_command_handler,
)
from app.packaging.domain.commands.recipe import (
    check_recipe_version_testing_environment_launch_status_command,
    check_recipe_version_testing_environment_setup_status_command,
    check_recipe_version_testing_test_status_command,
    complete_recipe_version_testing_command,
    launch_recipe_version_testing_environment_command,
    run_recipe_version_testing_command,
    setup_recipe_version_testing_environment_command,
)
from app.packaging.entrypoints.recipe_version_testing import config
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

    system_configuration_mapping = json.loads(
        parameters.get_parameter(app_config.get_system_config_mapping_param_name())
    )

    component_version_qry_srv = dynamodb_component_version_query_service.DynamoDBComponentVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_status_key(),
    )

    recipe_qry_srv = dynamodb_recipe_query_service.DynamoDBRecipeQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    recipe_version_qry_srv = dynamodb_recipe_version_query_service.DynamoDBRecipeVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_status_key(),
    )

    recipe_version_test_execution_qry_srv = (
        dynamodb_recipe_version_test_execution_query_service.DynamoDBRecipeVersionTestExecutionQueryService(
            table_name=app_config.get_table_name(),
            dynamodb_client=dynamodb.meta.client,
            gsi_name_entities=app_config.get_gsi_name_entities(),
        )
    )

    ami_factory_subnet_names = app_config.get_ami_factory_subnet_names().split(",")

    recipe_version_testing_srv = aws_recipe_version_testing_service.AwsRecipeVersionTestingService(
        boto_session=session,
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        ami_factory_subnet_names=ami_factory_subnet_names,
        instance_profile_name=app_config.get_instance_profile_name(),
        instance_security_group_name=app_config.get_instance_security_group_name(),
        region=app_config.get_default_region(),
        system_configuration_mapping=system_configuration_mapping,
        ssm_run_command_timeout=app_config.get_ssm_run_command_timeout(),
        recipe_test_s3_bucket_name=app_config.get_recipe_test_bucket_name(),
    )

    def _launch_recipe_version_testing_environment_command_factory():
        def _handle_command(
            command: launch_recipe_version_testing_environment_command.LaunchRecipeVersionTestingEnvironmentCommand,
        ):
            return launch_recipe_version_testing_environment_command_handler.handle(
                command=command,
                recipe_qry_srv=recipe_qry_srv,
                recipe_version_qry_srv=recipe_version_qry_srv,
                recipe_version_testing_srv=recipe_version_testing_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _check_recipe_version_testing_environment_launch_status_command_factory():
        def _handle_command(
            command: check_recipe_version_testing_environment_launch_status_command.CheckRecipeVersionTestingEnvironmentLaunchStatusCommand,
        ):
            return check_recipe_version_testing_environment_launch_status_command_handler.handle(
                command=command,
                recipe_version_test_execution_qry_srv=recipe_version_test_execution_qry_srv,
                recipe_version_testing_srv=recipe_version_testing_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _setup_recipe_version_testing_environment_command_factory():
        def _handle_command(
            command: setup_recipe_version_testing_environment_command.SetupRecipeVersionTestingEnvironmentCommand,
        ):
            return setup_recipe_version_testing_environment_command_handler.handle(
                command=command,
                recipe_version_test_execution_qry_srv=recipe_version_test_execution_qry_srv,
                recipe_version_testing_srv=recipe_version_testing_srv,
                logger=logger,
                uow=shared_uow,
            )

        return _handle_command

    def _check_recipe_version_testing_environment_setup_status_command_factory():
        def _handle_command(
            command: check_recipe_version_testing_environment_setup_status_command.CheckRecipeVersionTestingEnvironmentSetupStatusCommand,
        ):
            return check_recipe_version_testing_environment_setup_status_command_handler.handle(
                command=command,
                recipe_version_test_execution_qry_srv=recipe_version_test_execution_qry_srv,
                recipe_version_testing_srv=recipe_version_testing_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _run_recipe_version_testing_command_factory():
        def _handle_command(
            command: run_recipe_version_testing_command.RunRecipeVersionTestingCommand,
        ):
            return run_recipe_version_testing_command_handler.handle(
                command=command,
                recipe_version_qry_srv=recipe_version_qry_srv,
                recipe_version_test_execution_qry_srv=recipe_version_test_execution_qry_srv,
                recipe_version_testing_srv=recipe_version_testing_srv,
                component_version_qry_srv=component_version_qry_srv,
                logger=logger,
                uow=shared_uow,
            )

        return _handle_command

    def _check_recipe_version_testing_test_status_command_factory():
        def _handle_command(
            command: check_recipe_version_testing_test_status_command.CheckRecipeVersionTestingTestStatusCommand,
        ):
            return check_recipe_version_testing_test_status_command_handler.handle(
                command=command,
                recipe_version_test_execution_qry_srv=recipe_version_test_execution_qry_srv,
                recipe_version_testing_srv=recipe_version_testing_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _complete_recipe_version_testing_command_factory():
        def _handle_command(
            command: complete_recipe_version_testing_command.CompleteRecipeVersionTestingCommand,
        ):
            return complete_recipe_version_testing_command_handler.handle(
                command=command,
                recipe_qry_srv=recipe_qry_srv,
                recipe_version_test_execution_qry_srv=recipe_version_test_execution_qry_srv,
                recipe_version_testing_srv=recipe_version_testing_srv,
                uow=shared_uow,
            )

        return _handle_command

    metrics_client = power_tools_metrics.PowerToolsMetrics()

    cmd_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            launch_recipe_version_testing_environment_command.LaunchRecipeVersionTestingEnvironmentCommand,
            _launch_recipe_version_testing_environment_command_factory(),
        )
        .register_handler(
            check_recipe_version_testing_environment_launch_status_command.CheckRecipeVersionTestingEnvironmentLaunchStatusCommand,
            _check_recipe_version_testing_environment_launch_status_command_factory(),
        )
        .register_handler(
            setup_recipe_version_testing_environment_command.SetupRecipeVersionTestingEnvironmentCommand,
            _setup_recipe_version_testing_environment_command_factory(),
        )
        .register_handler(
            check_recipe_version_testing_environment_setup_status_command.CheckRecipeVersionTestingEnvironmentSetupStatusCommand,
            _check_recipe_version_testing_environment_setup_status_command_factory(),
        )
        .register_handler(
            run_recipe_version_testing_command.RunRecipeVersionTestingCommand,
            _run_recipe_version_testing_command_factory(),
        )
        .register_handler(
            check_recipe_version_testing_test_status_command.CheckRecipeVersionTestingTestStatusCommand,
            _check_recipe_version_testing_test_status_command_factory(),
        )
        .register_handler(
            complete_recipe_version_testing_command.CompleteRecipeVersionTestingCommand,
            _complete_recipe_version_testing_command_factory(),
        )
    )

    return Dependencies(
        command_bus=cmd_bus,
        uow=shared_uow,
    )
