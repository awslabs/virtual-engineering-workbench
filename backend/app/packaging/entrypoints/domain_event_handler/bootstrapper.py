import json

import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from pydantic import BaseModel

from app.packaging.adapters.query_services import (
    dynamodb_component_query_service,
    dynamodb_component_version_query_service,
    dynamodb_pipeline_query_service,
    dynamodb_recipe_query_service,
    dynamodb_recipe_version_query_service,
)
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.services import (
    aws_component_definition_service,
    ec2_image_builder_component_service,
    ec2_image_builder_pipeline_service,
    ec2_image_builder_recipe_service,
)
from app.packaging.domain.command_handlers.component import (
    deploy_component_version_command_handler,
    remove_component_version_command_handler,
    update_component_version_associations_command_handler,
)
from app.packaging.domain.command_handlers.pipeline import (
    deploy_pipeline_command_handler,
    remove_pipeline_command_handler,
)
from app.packaging.domain.command_handlers.recipe import (
    deploy_recipe_version_command_handler,
    remove_recipe_version_command_handler,
    update_recipe_version_associations_command_handler,
    update_recipe_version_on_component_update_command_handler,
)
from app.packaging.domain.commands.component import (
    deploy_component_version_command,
    remove_component_version_command,
    update_component_version_associations_command,
)
from app.packaging.domain.commands.pipeline import (
    deploy_pipeline_command,
    remove_pipeline_command,
)
from app.packaging.domain.commands.recipe import (
    deploy_recipe_version_command,
    remove_recipe_version_command,
    update_recipe_version_associations_command,
    update_recipe_version_on_component_update_command,
)
from app.packaging.domain.ports import component_version_definition_service
from app.packaging.entrypoints.domain_event_handler import config
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
    component_definition_service: component_version_definition_service.ComponentVersionDefinitionService

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

    component_version_service = ec2_image_builder_component_service.Ec2ImageBuilderComponentService(
        boto_session=session,
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        region=app_config.get_default_region(),
    )

    component_version_definition_service = aws_component_definition_service.AWSComponentDefinitionService(
        boto_session=session,
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        region=app_config.get_default_region(),
        bucket_name=app_config.get_component_bucket_name(),
    )

    component_version_query_service = dynamodb_component_version_query_service.DynamoDBComponentVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_custom_status_key(),
    )

    recipe_version_definition_service = aws_component_definition_service.AWSComponentDefinitionService(
        boto_session=session,
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        region=app_config.get_default_region(),
        bucket_name=app_config.get_recipe_bucket_name(),
    )

    component_query_service = dynamodb_component_query_service.DynamoDBComponentQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_pk(),
    )

    recipe_version_service = ec2_image_builder_recipe_service.Ec2ImageBuilderRecipeService(
        boto_session=session,
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        image_key_name=app_config.get_image_key_name(),
        region=app_config.get_default_region(),
    )

    recipe_query_service = dynamodb_recipe_query_service.DynamoDBRecipeQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )

    pipeline_qry_srv = dynamodb_pipeline_query_service.DynamoDBPipelineQueryService(
        dynamodb_client=dynamodb.meta.client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_pk(),
        gsi_name_entities=app_config.get_gsi_name_entities(),
        table_name=app_config.get_table_name(),
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
        topic_arn=(
            f"arn:aws:sns:{app_config.get_default_region()}:"
            f"{app_config.get_ami_factory_account_id()}:{app_config.get_topic_name()}"
        ),
    )

    recipe_version_qry_srv = dynamodb_recipe_version_query_service.DynamoDBRecipeVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb.meta.client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_custom_status_key(),
    )

    def _update_recipe_version_on_component_update_command_handler_factory():
        def _handle_command(
            command: update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand,
        ):
            return update_recipe_version_on_component_update_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_qry_srv=component_query_service,
                component_version_qry_srv=component_version_query_service,
                recipe_version_query_service=recipe_version_qry_srv,
            )

        return _handle_command

    def _deploy_component_version_cmd_handler_factory():
        def _handle_command(
            command: deploy_component_version_command.DeployComponentVersionCommand,
        ):
            return deploy_component_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                component_version_service=component_version_service,
                component_version_definition_service=component_version_definition_service,
                component_query_service=component_query_service,
                logger=logger,
            )

        return _handle_command

    def _remove_recipe_version_cmd_handler_factory():
        def _handle_command(
            command: remove_recipe_version_command.RemoveRecipeVersionCommand,
        ):
            return remove_recipe_version_command_handler.handle(
                command=command,
                message_bus=message_bus,
                uow=shared_uow,
                component_version_service=component_version_service,
                recipe_version_service=recipe_version_service,
            )

        return _handle_command

    def _remove_component_version_cmd_handler_factory():
        def _handle_command(
            command: remove_component_version_command.RemoveComponentVersionCommand,
        ):
            return remove_component_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                component_version_service=component_version_service,
                component_version_definition_service=component_version_definition_service,
                logger=logger,
            )

        return _handle_command

    def _deploy_recipe_version_cmd_handler_factory():
        def _handle_command(
            command: deploy_recipe_version_command.DeployRecipeVersionCommand,
        ):
            return deploy_recipe_version_command_handler.handle(
                command=command,
                uow=shared_uow,
                message_bus=message_bus,
                recipe_version_service=recipe_version_service,
                recipe_component_definition_service=recipe_version_definition_service,
                recipe_query_service=recipe_query_service,
                component_version_query_service=component_version_query_service,
                component_version_service=component_version_service,
                logger=logger,
            )

        return _handle_command

    def _deploy_pipeline_cmd_handler_factory():
        def _handle_command(command: deploy_pipeline_command.DeployPipelineCommand):
            return deploy_pipeline_command_handler.handle(
                command=command,
                logger=logger,
                pipeline_qry_srv=pipeline_qry_srv,
                pipeline_srv=pipeline_srv,
                recipe_version_qry_srv=recipe_version_qry_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _remove_pipeline_cmd_handler_factory():
        def _handle_command(command: remove_pipeline_command.RemovePipelineCommand):
            return remove_pipeline_command_handler.handle(
                command=command,
                pipeline_srv=pipeline_srv,
                uow=shared_uow,
            )

        return _handle_command

    def _update_component_version_associations_cmd_handler_factory():
        def _handle_command(
            command: update_component_version_associations_command.UpdateComponentVersionAssociationsCommand,
        ):
            return update_component_version_associations_command_handler.handle(
                command=command,
                component_version_qry_srv=component_version_query_service,
                logger=logger,
                uow=shared_uow,
            )

        return _handle_command

    def _update_recipe_version_associations_cmd_handler_factory():
        def _handle_command(
            command: update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand,
        ):
            return update_recipe_version_associations_command_handler.handle(
                command=command,
                recipe_version_qry_svc=recipe_version_qry_srv,
                component_version_qry_svc=component_version_query_service,
                uow=shared_uow,
                logger=logger,
            )

        return _handle_command

    command_bus = (
        command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        )
        .register_handler(
            deploy_component_version_command.DeployComponentVersionCommand,
            _deploy_component_version_cmd_handler_factory(),
        )
        .register_handler(
            remove_recipe_version_command.RemoveRecipeVersionCommand,
            _remove_recipe_version_cmd_handler_factory(),
        )
        .register_handler(
            remove_component_version_command.RemoveComponentVersionCommand,
            _remove_component_version_cmd_handler_factory(),
        )
        .register_handler(
            deploy_recipe_version_command.DeployRecipeVersionCommand,
            _deploy_recipe_version_cmd_handler_factory(),
        )
        .register_handler(
            deploy_pipeline_command.DeployPipelineCommand,
            _deploy_pipeline_cmd_handler_factory(),
        )
        .register_handler(
            remove_pipeline_command.RemovePipelineCommand,
            _remove_pipeline_cmd_handler_factory(),
        )
        .register_handler(
            update_component_version_associations_command.UpdateComponentVersionAssociationsCommand,
            _update_component_version_associations_cmd_handler_factory(),
        )
        .register_handler(
            update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand,
            _update_recipe_version_associations_cmd_handler_factory(),
        )
        .register_handler(
            update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand,
            _update_recipe_version_on_component_update_command_handler_factory(),
        )
    )

    return Dependencies(
        command_bus=command_bus,
        component_definition_service=component_version_definition_service,
    )
