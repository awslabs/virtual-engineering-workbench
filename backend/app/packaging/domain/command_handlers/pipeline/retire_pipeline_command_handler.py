from datetime import datetime, timezone

from app.packaging.domain.commands.pipeline import retire_pipeline_command
from app.packaging.domain.events.pipeline import pipeline_retirement_started
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.model.pipeline import pipeline
from app.packaging.domain.ports import pipeline_query_service
from app.shared.adapters.message_bus.message_bus import MessageBus
from app.shared.adapters.unit_of_work_v2.unit_of_work import UnitOfWork


def handle(
    command: retire_pipeline_command.RetirePipelineCommand,
    pipeline_qry_srv: pipeline_query_service.PipelineQueryService,
    message_bus: MessageBus,
    uow: UnitOfWork,
):
    pipeline_entity = pipeline_qry_srv.get_pipeline(
        project_id=command.projectId.value, pipeline_id=command.pipelineId.value
    )

    if pipeline_entity is None:
        raise DomainException(f"Pipeline {command.pipelineId.value} can not be found.")

    acceptable_states_for_retirement = [
        pipeline.PipelineStatus.Created,
        pipeline.PipelineStatus.Failed,
    ]

    if pipeline_entity.status not in acceptable_states_for_retirement:
        raise DomainException(
            f"Pipeline {command.pipelineId.value} can not be retired while in {pipeline_entity.status} status."
        )

    current_time = datetime.now(timezone.utc).isoformat()

    with uow:
        uow.get_repository(pipeline.PipelinePrimaryKey, pipeline.Pipeline).update_attributes(
            pipeline.PipelinePrimaryKey(
                projectId=command.projectId.value,
                pipelineId=command.pipelineId.value,
            ),
            lastUpdateDate=current_time,
            lastUpdateBy=command.lastUpdateBy.value,
            status=pipeline.PipelineStatus.Updating,
        )
        uow.commit()

    kwargs = {"projectId": command.projectId.value, "pipelineId": command.pipelineId.value}
    if pipeline_entity.distributionConfigArn:
        kwargs["distributionConfigArn"] = pipeline_entity.distributionConfigArn
    if pipeline_entity.infrastructureConfigArn:
        kwargs["infrastructureConfigArn"] = pipeline_entity.infrastructureConfigArn
    if pipeline_entity.pipelineArn:
        kwargs["pipelineArn"] = pipeline_entity.pipelineArn

    message_bus.publish(pipeline_retirement_started.PipelineRetirementStarted(**kwargs))
