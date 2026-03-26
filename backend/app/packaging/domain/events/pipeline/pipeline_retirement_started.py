from typing import Optional

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class PipelineRetirementStarted(message_bus.Message):
    event_name: str = Field("PipelineRetirementStarted", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    pipeline_id: str = Field(..., alias="pipelineId")
    distributionConfigArn: Optional[str] = Field(None, title="distributionConfigArn")
    infrastructureConfigArn: Optional[str] = Field(None, title="infrastructureConfigArn")
    pipelineArn: Optional[str] = Field(None, title="pipelineArn")

    class Config:
        allow_population_by_field_name = True
