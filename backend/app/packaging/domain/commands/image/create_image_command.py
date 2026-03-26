from app.packaging.domain.value_objects.pipeline import pipeline_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class CreateImageCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    pipelineId: pipeline_id_value_object.PipelineIdValueObject
