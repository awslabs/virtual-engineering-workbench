from datetime import datetime, timezone

from app.packaging.domain.commands.pipeline import update_pipeline_command
from app.packaging.domain.events.pipeline import pipeline_update_started
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.model.recipe import recipe_version
from app.packaging.domain.ports import (
    pipeline_query_service,
    pipeline_service,
    recipe_query_service,
    recipe_version_query_service,
)
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def _update_attributes(
    pipeline_entity: pipeline.Pipeline,
    recipe_version_entity: recipe_version.RecipeVersion,
    command: update_pipeline_command.UpdatePipelineCommand,
    uow: unit_of_work.UnitOfWork,
):
    with uow:
        kwargs = {
            "lastUpdateDate": datetime.now(timezone.utc).isoformat(),
            "lastUpdatedBy": command.lastUpdatedBy.value,
            "status": pipeline.PipelineStatus.Updating,
        }
        if command.recipeVersionId:
            kwargs["recipeVersionId"] = command.recipeVersionId.value
            kwargs["recipeVersionName"] = recipe_version_entity.recipeVersionName
        if command.buildInstanceTypes:
            kwargs["buildInstanceTypes"] = command.buildInstanceTypes.value
        if command.pipelineSchedule:
            kwargs["pipelineSchedule"] = command.pipelineSchedule.value
        kwargs["productId"] = command.productId.value if command.productId else None
        uow.get_repository(pipeline.PipelinePrimaryKey, pipeline.Pipeline).update_attributes(
            pipeline.PipelinePrimaryKey(pipelineId=pipeline_entity.pipelineId, projectId=pipeline_entity.projectId),
            **kwargs,
        )
        uow.commit()


def __check_allowed_buildinstance_types(
    command: update_pipeline_command.UpdatePipelineCommand,
    pipeline_entity: pipeline.Pipeline,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    pipeline_srv: pipeline_service.PipelineService,
):
    if command.buildInstanceTypes:
        recipe_entity = recipe_qry_srv.get_recipe(
            recipe_id=pipeline_entity.recipeId, project_id=pipeline_entity.projectId
        )
        if recipe_entity is None:
            raise domain_exception.DomainException(f"No recipe {pipeline_entity.recipeId} found.")
        allowed_build_types = pipeline_srv.get_pipeline_allowed_build_instance_types(
            architecture=recipe_entity.recipeArchitecture
        )
        for build_type in command.buildInstanceTypes.value:
            if build_type not in allowed_build_types:
                raise domain_exception.DomainException(
                    f"Build instance type {build_type} is not allowed for recipe {pipeline_entity.recipeId}."
                )


def handle(
    command: update_pipeline_command.UpdatePipelineCommand,
    message_bus: message_bus.MessageBus,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    pipeline_qry_srv: pipeline_query_service.PipelineQueryService,
    recipe_qry_srv: recipe_query_service.RecipeQueryService,
    pipeline_srv: pipeline_service.PipelineService,
    uow: unit_of_work.UnitOfWork,
):
    pipeline_entity = pipeline_qry_srv.get_pipeline(
        pipeline_id=command.pipelineId.value, project_id=command.projectId.value
    )

    if pipeline_entity is None:
        raise domain_exception.DomainException(f"Pipeline {command.pipelineId.value} can not be found.")
    if pipeline_entity.status not in [pipeline.PipelineStatus.Created, pipeline.PipelineStatus.Failed]:
        raise domain_exception.DomainException(
            f"Pipeline status should be {pipeline.PipelineStatus.Created.value} or "
            f"{pipeline.PipelineStatus.Failed.value} to allow update, but is {pipeline_entity.status.value}."
        )

    version_id = command.recipeVersionId.value if command.recipeVersionId else pipeline_entity.recipeVersionId
    recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
        recipe_id=pipeline_entity.recipeId, version_id=version_id
    )

    if recipe_version_entity is None:
        raise domain_exception.DomainException(f"No recipe version {version_id} found for {pipeline_entity.recipeId}.")
    if recipe_version_entity.status != recipe_version.RecipeVersionStatus.Released:
        raise domain_exception.DomainException(
            f"Version {version_id} of recipe {pipeline_entity.recipeId} has not been released."
        )
    __check_allowed_buildinstance_types(command, pipeline_entity, recipe_qry_srv, pipeline_srv)

    _update_attributes(pipeline_entity, recipe_version_entity, command, uow)

    message_bus.publish(
        pipeline_update_started.PipelineUpdateStarted(
            projectId=pipeline_entity.projectId,
            pipelineId=pipeline_entity.pipelineId,
        )
    )
