from datetime import datetime, timezone

from app.packaging.domain.commands.pipeline import create_pipeline_command
from app.packaging.domain.events.pipeline import pipeline_creation_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import pipeline_service, recipe_query_service, recipe_version_query_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: create_pipeline_command.CreatePipelineCommand,
    message_bus: message_bus.MessageBus,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    pipeline_srv: pipeline_service.PipelineService,
    uow: unit_of_work.UnitOfWork,
):
    recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
        recipe_id=command.recipeId.value, version_id=command.recipeVersionId.value
    )

    if recipe_version_entity is None:
        raise domain_exception.DomainException(
            f"No recipe version {command.recipeVersionId.value} found for {command.recipeId.value}."
        )
    if recipe_version_entity.status != recipe_version.RecipeVersionStatus.Released:
        raise domain_exception.DomainException(
            f"Version {command.recipeVersionId.value} of recipe {command.recipeId.value} has not been released."
        )
    recipe_entity = recipe_qry_srv.get_recipe(recipe_id=command.recipeId.value, project_id=command.projectId.value)
    if recipe_entity is None:
        raise domain_exception.DomainException(f"No recipe {command.recipeId.value} found.")
    allowed_build_types = pipeline_srv.get_pipeline_allowed_build_instance_types(
        architecture=recipe_entity.recipeArchitecture
    )
    for build_type in command.buildInstanceTypes.value:
        if build_type not in allowed_build_types:
            raise domain_exception.DomainException(
                f"Build instance type {build_type} is not allowed for recipe {command.recipeId.value}."
            )

    current_time = datetime.now(timezone.utc).isoformat()
    pipeline_entity = pipeline.Pipeline(
        projectId=command.projectId.value,
        buildInstanceTypes=command.buildInstanceTypes.value,
        pipelineDescription=command.pipelineDescription.value,
        pipelineName=command.pipelineName.value,
        pipelineSchedule=command.pipelineSchedule.value,
        recipeId=command.recipeId.value,
        recipeName=recipe_version_entity.recipeName,
        recipeVersionId=command.recipeVersionId.value,
        recipeVersionName=recipe_version_entity.recipeVersionName,
        status=pipeline.PipelineStatus.Creating,
        productId=command.productId.value if command.productId else None,
        createDate=current_time,
        lastUpdateDate=current_time,
        createdBy=command.createdBy.value,
        lastUpdatedBy=command.createdBy.value,
    )

    with uow:
        uow.get_repository(repo_key=pipeline.PipelinePrimaryKey, repo_type=pipeline.Pipeline).add(pipeline_entity)
        uow.commit()

    message_bus.publish(
        pipeline_creation_started.PipelineCreationStarted(
            projectId=command.projectId.value,
            pipelineId=pipeline_entity.pipelineId,
        )
    )
