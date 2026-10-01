import json
from typing import Any

import boto3
from aws_lambda_powertools import logging
from aws_lambda_powertools.utilities import parameters
from pydantic import BaseModel, ConfigDict

from app.packaging.adapters.query_services import (
    dynamodb_component_query_service,
    dynamodb_component_version_query_service,
    dynamodb_image_query_service,
    dynamodb_mandatory_components_list_query_service,
    dynamodb_pipeline_query_service,
    dynamodb_recipe_query_service,
    dynamodb_recipe_version_query_service,
)
from app.packaging.adapters.repository import dynamo_entity_config
from app.packaging.adapters.services import (
    aws_component_definition_service,
    ec2_image_builder_pipeline_service,
    parameter_service,
)
from app.packaging.adapters.services.projects_api_service_client_project_access_service import (
    ProjectsApiServiceClientProjectAccessService,
)
from app.packaging.domain.command_handlers.component import (
    archive_component_command_handler,
    create_component_command_handler,
    create_component_version_command_handler,
    release_component_version_command_handler,
    retire_component_version_command_handler,
    update_component_command_handler,
    update_component_version_command_handler,
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
    release_component_version_command,
    retire_component_version_command,
    update_component_command,
    update_component_version_command,
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
from app.packaging.domain.ports.service_client_project_access_service import ServiceClientProjectAccessService
from app.packaging.domain.query_services import (
    component_domain_query_service,
    component_version_domain_query_service,
    image_domain_query_service,
    pipeline_domain_query_service,
    recipe_domain_query_service,
    recipe_version_domain_query_service,
)
from app.packaging.entrypoints.s2s_api import config
from app.shared.adapters.message_bus import (
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
    project_access_service: ServiceClientProjectAccessService
    command_bus: Any
    recipe_domain_qry_srv: recipe_domain_query_service.RecipeDomainQueryService
    recipe_version_domain_qry_srv: recipe_version_domain_query_service.RecipeVersionDomainQueryService
    pipeline_domain_qry_srv: pipeline_domain_query_service.PipelineDomainQueryService
    image_domain_qry_srv: image_domain_query_service.ImageDomainQueryService
    component_domain_qry_srv: component_domain_query_service.ComponentDomainQueryService
    component_version_domain_qry_srv: component_version_domain_query_service.ComponentVersionDomainQueryService
    component_version_qry_srv: Any
    model_config = ConfigDict(arbitrary_types_allowed=True)


def bootstrap(app_config: config.AppConfig, logger: logging.Logger) -> Dependencies:  # noqa: C901
    session = boto_logger.loggable_session(boto3.session.Session(), logger)
    dynamodb = session.resource("dynamodb", region_name=app_config.get_default_region())
    dynamodb_client = dynamodb.meta.client
    uow = dynamodb_unit_of_work.DynamoDBUnitOfWork(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb_client,
        repo_factories=dynamo_entity_config.EntityConfigurator(table_name=app_config.get_table_name()).repo_factories(),
        logger=logger,
    )

    metrics_client = power_tools_metrics.PowerToolsMetrics()
    events_api = aws_events_api.AWSEventsApi(
        client=session.client("events", region_name=app_config.get_default_region())
    )
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

    component_query_service = dynamodb_component_query_service.DynamoDBComponentQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb_client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_pk(),
    )
    component_version_query_service = dynamodb_component_version_query_service.DynamoDBComponentVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb_client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_status_key(),
    )
    recipe_version_query_service = dynamodb_recipe_version_query_service.DynamoDBRecipeVersionQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb_client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_custom_query_by_status=app_config.get_gsi_name_query_by_status_key(),
    )
    recipe_query_service = dynamodb_recipe_query_service.DynamoDBRecipeQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb_client,
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )
    pipeline_query_service = dynamodb_pipeline_query_service.DynamoDBPipelineQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb_client,
        gsi_inverted_primary_key=app_config.get_gsi_name_inverted_pk(),
        gsi_name_entities=app_config.get_gsi_name_entities(),
    )
    image_query_service = dynamodb_image_query_service.DynamoDBImageQueryService(
        table_name=app_config.get_table_name(),
        dynamodb_client=dynamodb_client,
        gsi_custom_query_by_build_version_arn=app_config.get_gsi_name_query_by_build_version_arn(),
        gsi_custom_query_by_recipe_id_and_version=app_config.get_gsi_name_query_by_recipe_id_and_version(),
        gsi_name_entities=app_config.get_gsi_name_entities(),
        gsi_name_image_upstream_id=app_config.get_gsi_name_image_upstream_id(),
    )
    mandatory_components_list_query_service = (
        dynamodb_mandatory_components_list_query_service.DynamoDBMandatoryComponentsListQueryService(
            table_name=app_config.get_table_name(),
            dynamodb_client=dynamodb_client,
            gsi_name_entities=app_config.get_gsi_name_entities(),
        )
    )
    component_definition_service = aws_component_definition_service.AWSComponentDefinitionService(
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        bucket_name=app_config.get_component_bucket_name(),
        region=app_config.get_default_region(),
        boto_session=session,
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
    pipeline_service = ec2_image_builder_pipeline_service.Ec2ImageBuilderPipelineService(
        admin_role=app_config.get_admin_role(),
        ami_factory_aws_account_id=app_config.get_ami_factory_account_id(),
        ami_factory_subnet_names=app_config.get_ami_factory_subnet_names().split(","),
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

    def create_component(command):
        return create_component_command_handler.handle(command=command, uow=uow)

    def update_component(command):
        return update_component_command_handler.handle(command=command, uow=uow)

    def archive_component(command):
        return archive_component_command_handler.handle(
            command=command,
            component_qry_srv=component_query_service,
            component_version_qry_srv=component_version_query_service,
            uow=uow,
        )

    def create_version(command):
        return create_component_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            component_version_qry_srv=component_version_query_service,
            component_qry_srv=component_query_service,
        )

    def update_version(command):
        return update_component_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            component_version_qry_srv=component_version_query_service,
            component_qry_srv=component_query_service,
        )

    def release_version(command):
        return release_component_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            component_version_qry_srv=component_version_query_service,
            recipe_version_qry_srv=recipe_version_query_service,
        )

    def retire_version(command):
        return retire_component_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            component_version_query_service=component_version_query_service,
            mandatory_components_list_query_service=mandatory_components_list_query_service,
        )

    def create_recipe(command):
        return create_recipe_command_handler.handle(command=command, uow=uow)

    def archive_recipe(command):
        return archive_recipe_command_handler.handle(
            command=command,
            recipe_qry_srv=recipe_query_service,
            recipe_version_qry_srv=recipe_version_query_service,
            uow=uow,
        )

    def create_recipe_version(command):
        return create_recipe_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            component_version_qry_srv=component_version_query_service,
            recipe_version_qry_srv=recipe_version_query_service,
            recipe_qry_srv=recipe_query_service,
            parameter_srv=parameter_srv,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service,
            system_configuration_mapping=system_configuration_mapping,
            component_qry_srv=component_query_service,
        )

    def update_recipe_version(command):
        return update_recipe_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            component_version_qry_srv=component_version_query_service,
            recipe_version_query_service=recipe_version_query_service,
            recipe_qry_service=recipe_query_service,
            parameter_qry_srv=parameter_srv,
            mandatory_components_list_qry_srv=mandatory_components_list_query_service,
            system_configuration_mapping=system_configuration_mapping,
            component_qry_srv=component_query_service,
        )

    def release_recipe_version(command):
        return release_recipe_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            component_version_qry_srv=component_version_query_service,
            recipe_version_qry_srv=recipe_version_query_service,
        )

    def retire_recipe_version(command):
        return retire_recipe_version_command_handler.handle(
            command=command,
            uow=uow,
            message_bus=message_bus,
            recipe_version_query_service=recipe_version_query_service,
        )

    def create_pipeline(command):
        return create_pipeline_command_handler.handle(
            command=command,
            message_bus=message_bus,
            recipe_qry_srv=recipe_query_service,
            recipe_version_qry_srv=recipe_version_query_service,
            pipeline_srv=pipeline_service,
            uow=uow,
        )

    def update_pipeline(command):
        return update_pipeline_command_handler.handle(
            command=command,
            message_bus=message_bus,
            recipe_version_qry_srv=recipe_version_query_service,
            pipeline_qry_srv=pipeline_query_service,
            recipe_qry_srv=recipe_query_service,
            pipeline_srv=pipeline_service,
            uow=uow,
        )

    def retire_pipeline(command):
        return retire_pipeline_command_handler.handle(
            command=command,
            pipeline_qry_srv=pipeline_query_service,
            message_bus=message_bus,
            uow=uow,
        )

    def create_image(command):
        return create_image_command_handler.handle(
            command=command,
            pipeline_qry_srv=pipeline_query_service,
            pipeline_srv=pipeline_service,
            uow=uow,
        )

    command_bus = command_bus_metrics.CommandBusMetrics(
        inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
        metrics_client=metrics_client,
    )
    command_bus.register_handler(create_component_command.CreateComponentCommand, create_component).register_handler(
        update_component_command.UpdateComponentCommand, update_component
    ).register_handler(archive_component_command.ArchiveComponentCommand, archive_component).register_handler(
        create_component_version_command.CreateComponentVersionCommand, create_version
    ).register_handler(
        update_component_version_command.UpdateComponentVersionCommand, update_version
    ).register_handler(
        release_component_version_command.ReleaseComponentVersionCommand, release_version
    ).register_handler(
        retire_component_version_command.RetireComponentVersionCommand, retire_version
    ).register_handler(
        create_recipe_command.CreateRecipeCommand, create_recipe
    ).register_handler(
        archive_recipe_command.ArchiveRecipeCommand, archive_recipe
    ).register_handler(
        create_recipe_version_command.CreateRecipeVersionCommand, create_recipe_version
    ).register_handler(
        update_recipe_version_command.UpdateRecipeVersionCommand, update_recipe_version
    ).register_handler(
        release_recipe_version_command.ReleaseRecipeVersionCommand, release_recipe_version
    ).register_handler(
        retire_recipe_version_command.RetireRecipeVersionCommand, retire_recipe_version
    ).register_handler(
        create_pipeline_command.CreatePipelineCommand, create_pipeline
    ).register_handler(
        update_pipeline_command.UpdatePipelineCommand, update_pipeline
    ).register_handler(
        retire_pipeline_command.RetirePipelineCommand, retire_pipeline
    ).register_handler(
        create_image_command.CreateImageCommand, create_image
    )

    registry = service_registry.ServiceRegistry.from_config(
        app_config=app_config,
        ssm_client=session.client("ssm", region_name=app_config.get_default_region()),
        logger=logger,
    )
    project_access_service = ProjectsApiServiceClientProjectAccessService(
        api=registry.api_for(bounded_contexts.BoundedContext.PROJECTS)
    )
    return Dependencies(
        project_access_service=project_access_service,
        command_bus=command_bus,
        recipe_domain_qry_srv=recipe_domain_query_service.RecipeDomainQueryService(recipe_qry_srv=recipe_query_service),
        recipe_version_domain_qry_srv=recipe_version_domain_query_service.RecipeVersionDomainQueryService(
            recipe_qry_srv=recipe_query_service,
            recipe_version_qry_srv=recipe_version_query_service,
        ),
        pipeline_domain_qry_srv=pipeline_domain_query_service.PipelineDomainQueryService(
            pipeline_qry_srv=pipeline_query_service
        ),
        image_domain_qry_srv=image_domain_query_service.ImageDomainQueryService(image_qry_srv=image_query_service),
        component_domain_qry_srv=component_domain_query_service.ComponentDomainQueryService(
            component_qry_srv=component_query_service
        ),
        component_version_domain_qry_srv=component_version_domain_query_service.ComponentVersionDomainQueryService(
            component_qry_srv=component_query_service,
            component_version_qry_srv=component_version_query_service,
            component_version_definition_srv=component_definition_service,
        ),
        component_version_qry_srv=component_version_query_service,
    )
