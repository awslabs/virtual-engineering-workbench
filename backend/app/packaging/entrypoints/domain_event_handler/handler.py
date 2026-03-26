from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source
from aws_xray_sdk.core import patch_all

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
from app.packaging.domain.events.component import (
    component_version_creation_started,
    component_version_release_completed,
    component_version_retirement_started,
    component_version_update_started,
)
from app.packaging.domain.events.pipeline import (
    pipeline_creation_started,
    pipeline_retirement_started,
    pipeline_update_started,
)
from app.packaging.domain.events.recipe import (
    recipe_version_creation_started,
    recipe_version_release_completed,
    recipe_version_retirement_started,
    recipe_version_update_on_component_update_requested,
    recipe_version_update_started,
)
from app.packaging.domain.value_objects.component import (
    component_build_version_arn_value_object,
    component_id_value_object,
)
from app.packaging.domain.value_objects.component_version import (
    component_version_description_value_object,
    component_version_id_value_object,
    component_version_name_value_object,
    component_version_yaml_definition_value_object,
    components_versions_list_value_object,
)
from app.packaging.domain.value_objects.pipeline import (
    pipeline_arn_value_object,
    pipeline_distribution_config_arn_value_object,
    pipeline_id_value_object,
    pipeline_infrastructure_config_arn_value_object,
)
from app.packaging.domain.value_objects.recipe import (
    recipe_id_value_object,
    recipe_name_value_object,
)
from app.packaging.domain.value_objects.recipe_version import (
    recipe_version_arn_value_object,
    recipe_version_components_versions_value_object,
    recipe_version_id_value_object,
    recipe_version_name_value_object,
    recipe_version_parent_image_upstream_id_value_object,
    recipe_version_volume_size_value_object,
)
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
)
from app.packaging.entrypoints.domain_event_handler import bootstrapper, config
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig()
default_region_name = app_config.get_default_region()
secret_name = app_config.get_audit_logging_key_name()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

dependencies = bootstrapper.bootstrap(app_config, logger)
app = event_handler.EventBridgeEventResolver(logger=logger)


@app.handle(recipe_version_update_on_component_update_requested.RecipeVersionUpdateOnComponentUpdateRequested)
def update_recipe_version_on_component_update(
    event: recipe_version_update_on_component_update_requested.RecipeVersionUpdateOnComponentUpdateRequested,
):
    """Updates a specific recipe version when a component in rc is updated"""

    command = update_recipe_version_on_component_update_command.UpdateRecipeVersionOnComponentUpdateCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        lastUpdatedBy=user_id_value_object.from_str(event.last_updated_by),
    )

    dependencies.command_bus.handle(command)


@app.handle(component_version_creation_started.ComponentVersionCreationStarted)
def component_version_creation_started_handler(
    event: component_version_creation_started.ComponentVersionCreationStarted,
):
    command = deploy_component_version_command.DeployComponentVersionCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        componentVersionName=component_version_name_value_object.from_str(event.component_version_name),
        componentVersionDescription=component_version_description_value_object.from_str(
            event.component_version_description
        ),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            event.component_version_yaml_definition
        ),
    )

    dependencies.command_bus.handle(command)

    command = update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        componentsVersionDependencies=components_versions_list_value_object.from_list(
            event.component_version_dependencies
        ),
    )

    dependencies.command_bus.handle(command)


@app.handle(component_version_update_started.ComponentVersionUpdateStarted)
def component_version_update_started_handler(
    event: component_version_update_started.ComponentVersionUpdateStarted,
):
    command = deploy_component_version_command.DeployComponentVersionCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        componentVersionName=component_version_name_value_object.from_str(event.component_version_name),
        componentVersionDescription=component_version_description_value_object.from_str(
            event.component_version_description
        ),
        componentVersionYamlDefinition=component_version_yaml_definition_value_object.from_str(
            event.component_version_yaml_definition
        ),
    )

    dependencies.command_bus.handle(command)

    command = update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        componentsVersionDependencies=components_versions_list_value_object.from_list(
            event.component_version_dependencies
        ),
        previousComponentsVersionDependencies=components_versions_list_value_object.from_list(
            event.previous_component_version_dependencies
        ),
    )

    dependencies.command_bus.handle(command)


@app.handle(recipe_version_retirement_started.RecipeVersionRetirementStarted)
def recipe_version_retirement_started_handler(
    event: recipe_version_retirement_started.RecipeVersionRetirementStarted,
):
    command = remove_recipe_version_command.RemoveRecipeVersionCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeName=recipe_name_value_object.from_str(event.recipe_name),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        recipeVersionArn=recipe_version_arn_value_object.from_str(event.recipe_version_arn),
        recipeVersionComponentArn=component_build_version_arn_value_object.from_str(event.recipe_version_component_arn),
        recipeVersionName=recipe_version_name_value_object.from_str(event.recipe_version_name),
        lastUpdatedBy=user_id_value_object.from_str(event.last_updated_by),
    )

    dependencies.command_bus.handle(command)

    command = update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand(
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        # No current components versions list as the recipe version is retired at this point in time
        componentsVersionsList=components_versions_list_value_object.from_list(list()),
        # The retired recipe version reference has to be removed from its former components versions
        previousComponentsVersionsList=components_versions_list_value_object.from_list(event.recipe_component_versions),
    )

    dependencies.command_bus.handle(command)


@app.handle(component_version_retirement_started.ComponentVersionRetirementStarted)
def component_version_retirement_started_handler(
    event: component_version_retirement_started.ComponentVersionRetirementStarted,
):
    command = remove_component_version_command.RemoveComponentVersionCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        componentBuildVersionArn=component_build_version_arn_value_object.from_str(event.component_build_version_arn),
    )

    dependencies.command_bus.handle(command)

    command = update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        # This will remove all associations for the retired component version
        componentsVersionDependencies=components_versions_list_value_object.from_list(list()),
        previousComponentsVersionDependencies=components_versions_list_value_object.from_list(
            event.component_version_dependencies
        ),
    )

    dependencies.command_bus.handle(command)


@app.handle(component_version_release_completed.ComponentVersionReleaseCompleted)
def component_version_release_completed_handler(
    event: component_version_release_completed.ComponentVersionReleaseCompleted,
):
    command = update_component_version_associations_command.UpdateComponentVersionAssociationsCommand(
        componentId=component_id_value_object.from_str(event.component_id),
        componentVersionId=component_version_id_value_object.from_str(event.component_version_id),
        componentsVersionDependencies=components_versions_list_value_object.from_list(
            event.component_version_dependencies
        ),
    )

    dependencies.command_bus.handle(command)


@app.handle(recipe_version_creation_started.RecipeVersionCreationStarted)
def recipe_version_creation_started_handler(
    event: recipe_version_creation_started.RecipeVersionCreationStarted,
):
    command = deploy_recipe_version_command.DeployRecipeVersionCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        components=recipe_version_components_versions_value_object.from_list(event.recipe_component_versions),
        parentImageUpstreamId=recipe_version_parent_image_upstream_id_value_object.from_str(
            event.parent_image_upstream_id
        ),
        recipeVersionName=recipe_version_name_value_object.from_str(event.recipe_version_name),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(event.recipe_version_volume_size),
    )

    dependencies.command_bus.handle(command)

    command = update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand(
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        componentsVersionsList=components_versions_list_value_object.from_list(event.recipe_component_versions),
    )

    dependencies.command_bus.handle(command)


@app.handle(recipe_version_update_started.RecipeVersionUpdateStarted)
def recipe_version_update_started_handler(
    event: recipe_version_update_started.RecipeVersionUpdateStarted,
):
    command = deploy_recipe_version_command.DeployRecipeVersionCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        components=recipe_version_components_versions_value_object.from_list(event.recipe_components_versions),
        parentImageUpstreamId=recipe_version_parent_image_upstream_id_value_object.from_str(
            event.parent_image_upstream_id
        ),
        recipeVersionName=recipe_version_name_value_object.from_str(event.recipe_version_name),
        recipeVersionVolumeSize=recipe_version_volume_size_value_object.from_str(event.recipe_version_volume_size),
    )

    dependencies.command_bus.handle(command)

    command = update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand(
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        componentsVersionsList=components_versions_list_value_object.from_list(event.recipe_components_versions),
        previousComponentsVersionsList=components_versions_list_value_object.from_list(
            event.previous_recipe_components_versions
        ),
    )

    dependencies.command_bus.handle(command)


@app.handle(recipe_version_release_completed.RecipeVersionReleaseCompleted)
def recipe_version_release_completed_handler(
    event: recipe_version_release_completed.RecipeVersionReleaseCompleted,
):
    command = update_recipe_version_associations_command.UpdateRecipeVersionAssociationsCommand(
        recipeId=recipe_id_value_object.from_str(event.recipe_id),
        recipeVersionId=recipe_version_id_value_object.from_str(event.recipe_version_id),
        componentsVersionsList=components_versions_list_value_object.from_list(event.recipe_component_versions),
    )

    dependencies.command_bus.handle(command)


@app.handle(pipeline_creation_started.PipelineCreationStarted)
def pipeline_creation_started_handler(
    event: pipeline_creation_started.PipelineCreationStarted,
):
    command = deploy_pipeline_command.DeployPipelineCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        pipelineId=pipeline_id_value_object.from_str(event.pipeline_id),
    )

    dependencies.command_bus.handle(command)


@app.handle(pipeline_retirement_started.PipelineRetirementStarted)
def pipeline_retirement_started_handler(
    event: pipeline_retirement_started.PipelineRetirementStarted,
):
    command = remove_pipeline_command.RemovePipelineCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        pipelineId=pipeline_id_value_object.from_str(event.pipeline_id),
        distributionConfigArn=(
            pipeline_distribution_config_arn_value_object.from_str(event.distributionConfigArn)
            if event.distributionConfigArn
            else None
        ),
        infrastructureConfigArn=(
            pipeline_infrastructure_config_arn_value_object.from_str(event.infrastructureConfigArn)
            if event.infrastructureConfigArn
            else None
        ),
        pipelineArn=(pipeline_arn_value_object.from_str(event.pipelineArn) if event.pipelineArn else None),
    )

    dependencies.command_bus.handle(command)


@app.handle(pipeline_update_started.PipelineUpdateStarted)
def pipeline_update_started_handler(
    event: pipeline_update_started.PipelineUpdateStarted,
):
    command = deploy_pipeline_command.DeployPipelineCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        pipelineId=pipeline_id_value_object.from_str(event.pipeline_id),
    )

    dependencies.command_bus.handle(command)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.AsyncEventHandler: "DomainEvents"},
    enable_audit=True,
    region_name=default_region_name,
    secret_name=secret_name,
)
@event_source(data_class=EventBridgeEvent)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
