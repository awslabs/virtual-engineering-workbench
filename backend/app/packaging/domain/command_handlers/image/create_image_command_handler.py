from datetime import datetime, timezone

from app.packaging.domain.commands.image import create_image_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image import image
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.ports import pipeline_query_service, pipeline_service
from app.packaging.domain.value_objects.image import (
    image_build_version_arn_value_object,
    image_build_version_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: create_image_command.CreateImageCommand,
    pipeline_qry_srv: pipeline_query_service.PipelineQueryService,
    pipeline_srv: pipeline_service.PipelineService,
    uow: unit_of_work.UnitOfWork,
):
    pipeline_entity = pipeline_qry_srv.get_pipeline(
        pipeline_id=command.pipelineId.value, project_id=command.projectId.value
    )

    if pipeline_entity is None:
        raise domain_exception.DomainException(f"Pipeline {command.pipelineId.value} can not be found.")
    if pipeline_entity.status is not pipeline.PipelineStatus.Created:
        raise domain_exception.DomainException(
            f"Pipeline status should be {pipeline.PipelineStatus.Created.value} to "
            f"allow execution, but is {pipeline_entity.status.value}."
        )

    image_build_version_arn = image_build_version_arn_value_object.from_str(
        pipeline_srv.start_pipeline_execution(pipeline_arn=pipeline_entity.pipelineArn)
    ).value
    # Example ARN: arn:aws:imagebuilder:us-east-1:123456789012:image/my-recipe/1.0.0/1
    # Splitting based on character "/" will return my-recipe, 1.0.0 and 1 respectively
    image_build_version = image_build_version_value_object.from_int(int(image_build_version_arn.split("/")[3])).value

    current_time = datetime.now(timezone.utc).isoformat()
    image_entity = image.Image(
        projectId=command.projectId.value,
        imageBuildVersion=image_build_version,
        imageBuildVersionArn=image_build_version_arn,
        pipelineId=command.pipelineId.value,
        pipelineName=pipeline_entity.pipelineName,
        recipeId=pipeline_entity.recipeId,
        recipeName=pipeline_entity.recipeName,
        recipeVersionId=pipeline_entity.recipeVersionId,
        recipeVersionName=pipeline_entity.recipeVersionName,
        status=image.ImageStatus.Creating,
        createDate=current_time,
        lastUpdateDate=current_time,
    )

    with uow:
        uow.get_repository(repo_key=image.ImagePrimaryKey, repo_type=image.Image).add(image_entity)
        uow.commit()

    return image_entity.imageId
