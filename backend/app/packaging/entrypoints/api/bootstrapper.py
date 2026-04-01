import json

import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from pydantic import BaseModel, ConfigDict

from app.packaging.adapters.query_services import (
    dynamodb_component_query_service,
    dynamodb_component_version_query_service,
    dynamodb_component_version_test_execution_query_service,
    dynamodb_image_query_service,
    dynamodb_mandatory_components_list_query_service,
    dynamodb_pipeline_query_service,
    dynamodb_recipe_query_service,
    dynamodb_recipe_version_query_service,
    dynamodb_recipe_version_test_execution_query_service,
)
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.services import (
    aws_component_definition_service,
    ec2_image_builder_component_service,
    ec2_image_builder_pipeline_service,
    parameter_service,
)
from app.packaging.domain.command_handlers.component import (
    archive_component_command_handler,
    create_component_command_handler,
    create_component_version_command_handler,
    create_mandatory_components_list_command_handler,
    release_component_version_command_handler,
    retire_component_version_command_handler,
    share_component_command_handler,
    update_component_command_handler,
    update_component_version_command_handler,
    update_mandatory_components_list_command_handler,
    validate_component_version_command_handler,
)
from app.packaging.domain.command_handlers.image import create_image_command_handler
from app.packaging.domain.command_handlers.pipeline import (
    create_pipeline_command_handler,
    retire_pipeline_command_handler,
    update_pipeline_command_handler,
)
from app.packaging.domain.command_handlers.recipe import (
    archive_recipe_command_handler,
    create_recipe_command_handler,
    create_recipe_version_command_handler,
    release_recipe_version_command_handler,
    retire_recipe_version_command_handler,
    update_recipe_version_command_handler,
)
from app.packaging.domain.commands.component import (
    archive_component_command,
    create_component_command,
    create_component_version_command,
    create_mandatory_components_list_command,
    release_component_version_command,
    retire_component_version_command,
    share_component_command,
    update_component_command,
    update_component_version_command,
    update_mandatory_components_list_command,
    validate_component_version_command,
)
from app.packaging.domain.commands.image import create_image_command
from app.packaging.domain.commands.pipeline import (
    create_pipeline_command,
    retire_pipeline_command,
    update_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    archive_recipe_command,
    create_recipe_command,
    create_recipe_version_command,
    release_recipe_version_command,
    retire_recipe_version_command,
    update_recipe_version_command,
)
from app.packaging.domain.query_services import (
    component_domain_query_service,
    component_version_domain_query_service,
    component_version_test_execution_domain_query_service,
    image_domain_query_service,
    mandatory_components_list_domain_query_service,
    pipeline_domain_query_service,
    recipe_domain_query_service,
    recipe_version_domain_query_service,
    recipe_version_test_execution_domain_query_service,
)
from app.packaging.entrypoints.api import config
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
    component_domain_qry_srv: component_domain_query_service.ComponentDomainQueryService
    component_version_domain_qry_srv: component_version_domain_query_service.ComponentVersionDomainQueryService
    component_version_test_execution_domain_qry_srv: (
        component_version_test_execution_domain_query_service.ComponentVersionTestExecutionDomainQueryService
    )
    recipe_domain_qry_srv: recipe_domain_query_service.RecipeDomainQueryService
    recipe_version_domain_qry_srv: recipe_version_domain_query_service.RecipeVersionDomainQueryService
    image_domain_qry_srv: image_domain_query_service.ImageDomainQueryService
    pipeline_domain_qry_srv: pipeline_domain_query_service.PipelineDomainQueryService
    recipe_version_test_execution_domain_qry_srv: (
        recipe_version_test_execution_domain_query_service.RecipeVersionTestExecutionDomainQueryService
    )
    mandatory_components_list_domain_qry_srv: (
        mandatory_components_list_domain_query_service.MandatoryComponentsListDomainQueryService
    )
    pipeline_srv: ec2_image_builder_pipeline_service.Ec2ImageBuilderPipelineService
    component_definition_service: aws_component_definition_service.AWSComponentDefinitionService
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

    component_version_definition_srv = aws_component_definition_service.AWSComponentDefinitionService(
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        bucket_name=app_config.get_component_bucket_name(),
        region=app_config.get_default_region(),
        boto_session=session,
    )

    component_version_srv = ec2_image_builder_component_service.Ec2ImageBuilderComponentService(
        boto_session=session,
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        region=app_config.get_default_region(),
    )

    component_qry_srv = dynamodb_component_query_service.DynamoDBComponentQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_pk(),
    )

    component_version_qry_srv = dynamodb_component_version_query_service.DynamoDBComponentVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_status_key(),
    )

    mandatory_components_list_qry_srv = (
        dynamodb_mandatory_components_list_query_service.DynamoDBMandatoryComponentsListQueryService(
            table_name=app_config.get_table_name(),
            dynamodb_client=dynamodb.meta.client,
            gsi_name_entities=app_config.get_gsi_name_entities(),
        )
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

    image_qry_srv = dynamodb_image_query_service.DynamoDBImageQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_custom_query_by_build_version_arn=app_config.get_gsi_name_query_by_build_version_arn(),
        gsi_custom_query_by_recipe_id_and_version=app_config.get_gsi_name_query_by_recipe_id_and_version(),
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_name_image_upstream_id=app_config.get_gsi_name_image_upstream_id(),
    )

    pipeline_qry_srv = dynamodb_pipeline_query_service.DynamoDBPipelineQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_pk(),
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    parameter_srv = parameter_service.ParameterService(
        boto_session=session,
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        region=app_config.get_default_region(),
    )
    system_configuration_mapping = json.loads(
        parameters.get_parameter(app_config.get_system_config_mapping_param_name())
    )
    pipelines_configuration_mapping = json.loads(
        parameters.get_parameter(app_config.get_pipelines_config_mapping_param_name())
    )

    ami_factory_subnet_names = app_config.get_ami_factory_subnet_names().split(",")

    pipeline_srv = ec2_image_builder_pipeline_service.Ec2ImageBuilderPipelineService(
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        ami_factory_subnet_names=ami_factory_subnet_names,
        boto_session=session,
        image_key_name=app_config.get_image_key_name(),
        instance_profile_name=app_config.get_instance_profile_name(),
        instance_security_group_name=app_config.get_instance_security_group_name(),
        pipelines_configuration_mapping=pipelines_configuration_mapping,
        region=app_config.get_default_region(),
        topic_arn=f"arn:aws:sns:{app_config.get_default_region()}:{app_config.get_ami_factory_account_id()}:{app_config.get_topic_name()}",
    )

    component_domain_qry_srv = component_domain_query_service.ComponentDomainQueryService(
        component_qry_srv=dynamodb_component_query_service.DynamoDBComponentQueryService(
            table_name=app_config.get_table_name(),
            dynamodb_client=dynamodb.meta.client,
            gsi_name_entities=app_config.get_gsi_name_entities(),
            gsi_inverted_primary_key=app_config.get_gsi_name_inverted_pk(),
        )
    )

    component_version_domain_qry_srv = component_version_domain_query_service.ComponentVersionDomainQueryService(
        component_qry_srv=component_qry_srv,
        component_version_qry_srv=component_version_qry_srv,
        component_version_definition_srv=component_version_definition_srv,
    )

    component_version_test_execution_domain_qry_srv = component_version_test_execution_domain_query_service.ComponentVersionTestExecutionDomainQueryService(
        component_version_test_execution_qry_srv=dynamodb_component_version_test_execution_query_service.DynamoDBComponentVersionTestExecutionQueryService(
            table_name=app_config.get_table_name(),
            dynamodb_client=dynamodb.meta.client,
            gsi_name_entities=app_config.get_gsi_name_entities(),
        ),
        component_version_definition_srv=component_version_definition_srv,
    )

    mandatory_components_list_domain_qry_srv = (
        mandatory_components_list_domain_query_service.MandatoryComponentsListDomainQueryService(
            mandatory_components_list_qry_srv=mandatory_components_list_qry_srv
        )
    )

    recipe_domain_qry_srv = recipe_domain_query_service.RecipeDomainQueryService(
        recipe_qry_srv=dynamodb_recipe_query_service.DynamoDBRecipeQueryService(
            table_name=app_config.get_table_name(),
            dynamodb_client=dynamodb.meta.client,
            gsi_name_entities=app_config.get_gsi_name_entities(),
        )
    )

    recipe_version_domain_qry_srv = recipe_version_domain_query_service.RecipeVersionDomainQueryService(
        recipe_qry_srv=recipe_qry_srv, recipe_version_qry_srv=recipe_version_qry_srv
    )

    pipeline_domain_qry_srv = pipeline_domain_query_service.PipelineDomainQueryService(
        pipeline_qry_srv=pipeline_qry_srv
    )

    image_domain_qry_service = image_domain_query_service.ImageDomainQueryService(
        image_qry_srv=image_qry_srv,
    )

    recipe_version_test_execution_domain_qry_srv = recipe_version_test_execution_domain_query_service.RecipeVersionTestExecutionDomainQueryService(
        recipe_version_test_execution_qry_srv=dynamodb_recipe_version_test_execution_query_service.DynamoDBRecipeVersionTestExecutionQueryService(
            table_name=app_config.get_table_name(),
            dynamodb_client=dynamodb.meta.client,
            gsi_name_entities=app_config.get_gsi_name_entities(),
        ),
        component_version_definition_srv=component_version_definition_srv,
    )

    def _create_component_command_handler_factory():
        def _handle_command(
            command: create_component_command.CreateComponentCommand,
        ):
            return create_component_command_handler.handle(command=command, uow=shared_uow)

        return _handle_command

    def _share_component_command_handler_factory():
        def _handle_command(
            command: share_component_command.ShareComponentCommand,
        ):
            return share_component_command_handler.handle(
                command=command, component_qry_srv=component_qry_srv, uow=shared_uow
            )

        return _handle_command

    def _update_component_command_handler_factory():
        def _handle_command(
            command: update_component_command.UpdateComponentCommand,
        ):
            return update_component_command_handler.handle(command=command, uow=shared_uow)

        return _handle_command

    def _create_component_version_command_handler_factory():
        def _handle_command(
            command: create_component_version_command.CreateComponentVersionCommand,
        ):
            return create_component_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_qry_srv=component_version_qry_srv,
                component_qry_srv=component_qry_srv,
            )

        return _handle_command

    def _archive_component_version_command_handler_factory():
        def _handle_command(
            command: archive_component_command.ArchiveComponentCommand,
        ):
            return archive_component_command_handler.handle(
                command=command,
                component_qry_srv=component_qry_srv,
                component_version_qry_srv=component_version_qry_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _validate_component_version_command_handler_factory():
        def _handle_command(
            command: validate_component_version_command.ValidateComponentVersionCommand,
        ):
            return validate_component_version_command_handler.handle(
                command=command,
                component_version_service=component_version_srv,
                component_version_definition_service=component_version_definition_srv,
                component_query_service=component_qry_srv,
                logger=logger,
            )

        return _handle_command

    def _release_component_version_command_handler_factory():
        def _handle_command(
            command: release_component_version_command.ReleaseComponentVersionCommand,
        ):
            return release_component_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_qry_srv=component_version_qry_srv,
                recipe_version_qry_srv=recipe_version_qry_srv,
            )

        return _handle_command

    def _update_component_version_command_handler_factory():
        def _handle_command(
            command: update_component_version_command.UpdateComponentVersionCommand,
        ):
            return update_component_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_qry_srv=component_version_qry_srv,
            )

        return _handle_command

    def _create_recipe_command_handler_factory():
        def _handle_command(
            command: create_recipe_command.CreateRecipeCommand,
        ):
            return create_recipe_command_handler.handle(command=command, uow=shared_uow)

        return _handle_command

    def _archive_recipe_version_command_handler_factory():
        def _handle_command(
            command: archive_recipe_command.ArchiveRecipeCommand,
        ):
            return archive_recipe_command_handler.handle(
                command=command,
                recipe_qry_srv=recipe_qry_srv,
                recipe_version_qry_srv=recipe_version_qry_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _create_recipe_version_command_handler_factory() -> create_recipe_version_command_handler.handle:
        def _handle_command(
            command: create_recipe_version_command.CreateRecipeVersionCommand,
        ):
            return create_recipe_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_qry_srv=component_version_qry_srv,
                recipe_version_qry_srv=recipe_version_qry_srv,
                recipe_qry_srv=recipe_qry_srv,
                parameter_srv=parameter_srv,
                mandatory_components_list_qry_srv=mandatory_components_list_qry_srv,
                system_configuration_mapping=system_configuration_mapping,
            )

        return _handle_command

    def _retire_recipe_version_command_handler_factory():
        def _handle_command(
            command: retire_recipe_version_command.RetireRecipeVersionCommand,
        ):
            return retire_recipe_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                recipe_version_query_service=recipe_version_qry_srv,
            )

        return _handle_command

    def _retire_component_version_command_handler_factory():
        def _handle_command(
            command: retire_component_version_command.RetireComponentVersionCommand,
        ):
            return retire_component_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_query_service=component_version_qry_srv,
                mandatory_components_list_query_service=mandatory_components_list_qry_srv,
            )

        return _handle_command

    def _update_recipe_version_command_handler_factory():
        def _handle_command(
            command: update_recipe_version_command.UpdateRecipeVersionCommand,
        ):
            return update_recipe_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_qry_srv=component_version_qry_srv,
                recipe_version_query_service=recipe_version_qry_srv,
                recipe_qry_service=recipe_qry_srv,
                parameter_qry_srv=parameter_srv,
                mandatory_components_list_qry_srv=mandatory_components_list_qry_srv,
                system_configuration_mapping=system_configuration_mapping,
            )

        return _handle_command

    def _release_recipe_version_command_handler_factory():
        def _handle_command(
            command: release_recipe_version_command.ReleaseRecipeVersionCommand,
        ):
            return release_recipe_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_qry_srv=component_version_qry_srv,
                recipe_version_qry_srv=recipe_version_qry_srv,
            )

        return _handle_command

    def _create_mandatory_components_list_command_handler_factory():
        def _handle_command(
            command: create_mandatory_components_list_command.CreateMandatoryComponentsListCommand,
        ):
            return create_mandatory_components_list_command_handler.handle(
                command=command,
                component_version_qry_srv=component_version_qry_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _update_mandatory_components_list_command_handler_factory():
        def _handle_command(
            command: update_mandatory_components_list_command.UpdateMandatoryComponentsListCommand,
        ):
            return update_mandatory_components_list_command_handler.handle(
                command=command,
                component_version_qry_srv=component_version_qry_srv,
                mandatory_components_list_qry_srv=mandatory_components_list_qry_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _create_pipeline_command_handler_factory():
        def _handle_command(
            command: create_pipeline_command.CreatePipelineCommand,
        ):
            return create_pipeline_command_handler.handle(
                command=command,
                message_bus=message_bus,
                recipe_version_qry_srv=recipe_version_qry_srv,
                recipe_qry_srv=recipe_qry_srv,
                pipeline_srv=pipeline_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _retire_pipeline_command_handler_factory():
        def _handle_command(
            command: retire_pipeline_command.RetirePipelineCommand,
        ):
            return retire_pipeline_command_handler.handle(
                command=command,
                pipeline_qry_srv=pipeline_qry_srv,
                message_bus=message_bus,
                uow=shared_uow,
            )

        return _handle_command

    def _update_pipeline_command_handler_factory():
        def _handle_command(
            command: update_pipeline_command.UpdatePipelineCommand,
        ):
            return update_pipeline_command_handler.handle(
                command=command,
                message_bus=message_bus,
                recipe_version_qry_srv=recipe_version_qry_srv,
                pipeline_qry_srv=pipeline_qry_srv,
                recipe_qry_srv=recipe_qry_srv,
                pipeline_srv=pipeline_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _create_image_command_handler_factory():
        def _handle_command(
            command: create_image_command.CreateImageCommand,
        ):
            return create_image_command_handler.handle(
                command=command,
                pipeline_qry_srv=pipeline_qry_srv,
                pipeline_srv=pipeline_srv,
                uow=shared_uow,
            )

        return _handle_command

    cmd_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            create_component_command.CreateComponentCommand,
            _create_component_command_handler_factory(),
        )
        .register_handler(
            archive_component_command.ArchiveComponentCommand,
            _archive_component_version_command_handler_factory(),
        )
        .register_handler(
            share_component_command.ShareComponentCommand,
            _share_component_command_handler_factory(),
        )
        .register_handler(
            update_component_command.UpdateComponentCommand,
            _update_component_command_handler_factory(),
        )
        .register_handler(
            create_component_version_command.CreateComponentVersionCommand,
            _create_component_version_command_handler_factory(),
        )
        .register_handler(
            release_component_version_command.ReleaseComponentVersionCommand,
            _release_component_version_command_handler_factory(),
        )
        .register_handler(
            retire_component_version_command.RetireComponentVersionCommand,
            _retire_component_version_command_handler_factory(),
        )
        .register_handler(
            update_component_version_command.UpdateComponentVersionCommand,
            _update_component_version_command_handler_factory(),
        )
        .register_handler(
            create_mandatory_components_list_command.CreateMandatoryComponentsListCommand,
            _create_mandatory_components_list_command_handler_factory(),
        )
        .register_handler(
            update_mandatory_components_list_command.UpdateMandatoryComponentsListCommand,
            _update_mandatory_components_list_command_handler_factory(),
        )
        .register_handler(
            create_recipe_command.CreateRecipeCommand,
            _create_recipe_command_handler_factory(),
        )
        .register_handler(
            archive_recipe_command.ArchiveRecipeCommand,
            _archive_recipe_version_command_handler_factory(),
        )
        .register_handler(
            create_recipe_version_command.CreateRecipeVersionCommand,
            _create_recipe_version_command_handler_factory(),
        )
        .register_handler(
            retire_recipe_version_command.RetireRecipeVersionCommand,
            _retire_recipe_version_command_handler_factory(),
        )
        .register_handler(
            update_recipe_version_command.UpdateRecipeVersionCommand,
            _update_recipe_version_command_handler_factory(),
        )
        .register_handler(
            release_recipe_version_command.ReleaseRecipeVersionCommand,
            _release_recipe_version_command_handler_factory(),
        )
        .register_handler(
            create_pipeline_command.CreatePipelineCommand,
            _create_pipeline_command_handler_factory(),
        )
        .register_handler(
            retire_pipeline_command.RetirePipelineCommand,
            _retire_pipeline_command_handler_factory(),
        )
        .register_handler(
            update_pipeline_command.UpdatePipelineCommand,
            _update_pipeline_command_handler_factory(),
        )
        .register_handler(
            create_image_command.CreateImageCommand,
            _create_image_command_handler_factory(),
        )
        .register_handler(
            validate_component_version_command.ValidateComponentVersionCommand,
            _validate_component_version_command_handler_factory(),
        )
    )

    return Dependencies(
        command_bus=cmd_bus,
        uow=shared_uow,
        component_domain_qry_srv=component_domain_qry_srv,
        component_version_domain_qry_srv=component_version_domain_qry_srv,
        component_version_test_execution_domain_qry_srv=component_version_test_execution_domain_qry_srv,
        recipe_domain_qry_srv=recipe_domain_qry_srv,
        recipe_version_domain_qry_srv=recipe_version_domain_qry_srv,
        image_domain_qry_srv=image_domain_qry_service,
        recipe_version_test_execution_domain_qry_srv=recipe_version_test_execution_domain_qry_srv,
        mandatory_components_list_domain_qry_srv=mandatory_components_list_domain_qry_srv,
        pipeline_domain_qry_srv=pipeline_domain_qry_srv,
        pipeline_srv=pipeline_srv,
        component_definition_service=component_version_definition_srv,
    )
