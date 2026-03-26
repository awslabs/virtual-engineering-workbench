from app.packaging.domain.commands.pipeline import check_pipeline_update_status_command
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.ports import pipeline_query_service


def handle(
    command: check_pipeline_update_status_command.CheckPipelineUpdateStatusCommand,
    pipeline_query_service: pipeline_query_service.PipelineQueryService,
) -> dict[str, str]:
    pipeline_obj = pipeline_query_service.get_pipeline_by_pipeline_id(pipeline_id=command.pipelineId.value)

    if not pipeline_obj:
        return {"pipelineUpdateStatus": pipeline.PipelineStatus.Failed.value}

    status = pipeline_obj.status

    if status == pipeline.PipelineStatus.Created:
        return {"pipelineUpdateStatus": pipeline.PipelineStatus.Created.value}
    elif status in [pipeline.PipelineStatus.Failed]:
        return {"pipelineUpdateStatus": pipeline.PipelineStatus.Failed.value}
    else:
        return {"pipelineUpdateStatus": pipeline.PipelineStatus.Updating.value}
