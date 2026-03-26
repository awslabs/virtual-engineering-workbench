from app.packaging.domain.value_objects.pipeline import pipeline_id_value_object
from app.shared.adapters.message_bus import command_bus


class CheckPipelineUpdateStatusCommand(command_bus.Command):
    pipelineId: pipeline_id_value_object.PipelineIdValueObject
