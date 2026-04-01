from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class PipelineRetirementStarted(message_bus.Message):
    event_name: Literal["PipelineRetirementStarted"] = Field("PipelineRetirementStarted", alias="eventName")
    project_id: str = Field(..., alias="projectId")
    pipeline_id: str = Field(..., alias="pipelineId")
    distributionConfigArn: Optional[str] = Field(None, title="distributionConfigArn")
    infrastructureConfigArn: Optional[str] = Field(None, title="infrastructureConfigArn")
    pipelineArn: Optional[str] = Field(None, title="pipelineArn")
    model_config = ConfigDict(populate_by_name=True)
