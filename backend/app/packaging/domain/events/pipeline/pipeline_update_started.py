from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class PipelineUpdateStarted(message_bus.Message):
    event_name: str = Field("PipelineUpdateStarted", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    pipeline_id: str = Field(..., alias="pipelineId")

    class Config:
        allow_population_by_field_name = True
