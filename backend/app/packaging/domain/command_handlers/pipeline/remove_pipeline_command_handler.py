from datetime import datetime, timezone

from app.packaging.domain.commands.pipeline import remove_pipeline_command
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.ports import pipeline_service
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def handle(
    command: remove_pipeline_command.RemovePipelineCommand,
    pipeline_srv: pipeline_service.PipelineService,
    uow: unit_of_work.UnitOfWork,
):
    status = pipeline.PipelineStatus.Retired
    exception_message = f"Pipeline {command.pipelineId.value} can not be deleted."

    try:
        if command.pipelineArn:
            exception_message = f"Pipeline {command.pipelineArn.value} can not be deleted."

            pipeline_srv.delete_pipeline(pipeline_arn=command.pipelineArn.value)
        if command.infrastructureConfigArn:
            exception_message = (
                f"Pipeline infrastructure configuration {command.infrastructureConfigArn.value} can not be deleted."
            )

            pipeline_srv.delete_infrastructure_config(infrastructure_config_arn=command.infrastructureConfigArn.value)
        if command.distributionConfigArn:
            exception_message = (
                f"Pipeline distribution configuration {command.distributionConfigArn.value} can not be deleted."
            )

            pipeline_srv.delete_distribution_config(distribution_config_arn=command.distributionConfigArn.value)
    except:
        status = pipeline.PipelineStatus.Failed

        raise DomainException(exception_message)
    finally:
        current_time = datetime.now(timezone.utc).isoformat()

        with uow:
            uow.get_repository(pipeline.PipelinePrimaryKey, pipeline.Pipeline).update_attributes(
                pipeline.PipelinePrimaryKey(
                    projectId=command.projectId.value,
                    pipelineId=command.pipelineId.value,
                ),
                lastUpdateDate=current_time,
                status=status,
            )
            uow.commit()
