import logging

from app.packaging.domain.commands.pipeline import deploy_pipeline_command
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.ports import pipeline_query_service, pipeline_service, recipe_version_query_service
from app.packaging.domain.value_objects.pipeline import (
    pipeline_arn_value_object,
    pipeline_distribution_config_arn_value_object,
    pipeline_infrastructure_config_arn_value_object,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def __update_attributes(
    command: deploy_pipeline_command.DeployPipelineCommand,
    status: pipeline.PipelineStatus,
    uow: unit_of_work.UnitOfWork,
    distribution_config_arn: str | None = None,
    infrastructure_config_arn: str | None = None,
    pipeline_arn: str | None = None,
):
    with uow:
        kwargs = {"status": status}
        if distribution_config_arn:
            kwargs["distributionConfigArn"] = distribution_config_arn
        if infrastructure_config_arn:
            kwargs["infrastructureConfigArn"] = infrastructure_config_arn
        if pipeline_arn:
            kwargs["pipelineArn"] = pipeline_arn

        uow.get_repository(pipeline.PipelinePrimaryKey, pipeline.Pipeline).update_attributes(
            pipeline.PipelinePrimaryKey(pipelineId=command.pipelineId.value, projectId=command.projectId.value),
            **kwargs,
        )
        uow.commit()


def handle(
    command: deploy_pipeline_command.DeployPipelineCommand,
    logger: logging.Logger,
    pipeline_qry_srv: pipeline_query_service.PipelineQueryService,
    pipeline_srv: pipeline_service.PipelineService,
    recipe_version_qry_srv: recipe_version_query_service.RecipeVersionQueryService,
    uow: unit_of_work.UnitOfWork,
):
    try:
        kwargs = {"command": command, "status": pipeline.PipelineStatus.Created, "uow": uow}
        pipeline_entity = pipeline_qry_srv.get_pipeline(
            project_id=command.projectId.value, pipeline_id=command.pipelineId.value
        )

        if pipeline_entity is None:
            raise domain_exception.DomainException(f"Pipeline {command.pipelineId.value} can not be found.")

        recipe_version_entity = recipe_version_qry_srv.get_recipe_version(
            recipe_id=pipeline_entity.recipeId, version_id=pipeline_entity.recipeVersionId
        )

        if recipe_version_entity is None:
            raise domain_exception.DomainException(
                f"No recipe version {pipeline_entity.recipeVersionId} found for {pipeline_entity.recipeId}."
            )

        distribution_config_arn = (
            pipeline_srv.create_distribution_config(
                description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
                image_tags={
                    "Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"
                },
                name=pipeline_entity.pipelineId,
            )
            if not pipeline_entity.distributionConfigArn
            else pipeline_srv.update_distribution_config(
                description=f"Distribution configuration for {pipeline_entity.pipelineName} pipeline.",
                distribution_config_arn=pipeline_entity.distributionConfigArn,
                image_tags={
                    "Name": f"Version {recipe_version_entity.recipeVersionName} of {recipe_version_entity.recipeName}"
                },
            )
        )
        kwargs["distribution_config_arn"] = pipeline_distribution_config_arn_value_object.from_str(
            distribution_config_arn
        ).value
        infrastructure_config_arn = (
            pipeline_srv.create_infrastructure_config(
                description=f"Infrastructure configuration for {pipeline_entity.pipelineName} pipeline.",
                instance_types=pipeline_entity.buildInstanceTypes,
                name=pipeline_entity.pipelineId,
            )
            if not pipeline_entity.infrastructureConfigArn
            else pipeline_srv.update_infrastructure_config(
                description=f"Infrastructure configuration for {pipeline_entity.pipelineName} pipeline.",
                infrastructure_config_arn=pipeline_entity.infrastructureConfigArn,
                instance_types=pipeline_entity.buildInstanceTypes,
            )
        )
        kwargs["infrastructure_config_arn"] = pipeline_infrastructure_config_arn_value_object.from_str(
            infrastructure_config_arn
        ).value
        pipeline_arn = (
            pipeline_srv.create_pipeline(
                description=pipeline_entity.pipelineDescription,
                distribution_config_arn=kwargs["distribution_config_arn"],
                infrastructure_config_arn=kwargs["infrastructure_config_arn"],
                name=pipeline_entity.pipelineId,
                recipe_version_arn=recipe_version_entity.recipeVersionArn,
                schedule=pipeline_entity.pipelineSchedule,
            )
            if not pipeline_entity.pipelineArn
            else pipeline_srv.update_pipeline(
                description=pipeline_entity.pipelineDescription,
                distribution_config_arn=kwargs["distribution_config_arn"],
                infrastructure_config_arn=kwargs["infrastructure_config_arn"],
                pipeline_arn=pipeline_entity.pipelineArn,
                recipe_version_arn=recipe_version_entity.recipeVersionArn,
                schedule=pipeline_entity.pipelineSchedule,
            )
        )
        kwargs["pipeline_arn"] = pipeline_arn_value_object.from_str(pipeline_arn).value

        __update_attributes(**kwargs)
    except domain_exception.DomainException:
        kwargs["status"] = pipeline.PipelineStatus.Failed
        logger.exception(f"Pipeline {command.pipelineId.value} failed to deploy.", exc_info=True)
        __update_attributes(**kwargs)

        raise
    except Exception as exception:
        error_msg = f"Pipeline {command.pipelineId.value} failed to deploy."
        kwargs["status"] = pipeline.PipelineStatus.Failed

        logger.exception(error_msg, exc_info=True)
        __update_attributes(**kwargs)

        raise domain_exception.DomainException(error_msg) from exception
