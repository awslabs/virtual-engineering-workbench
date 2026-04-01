from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class TechnologyUpdated(message_bus.Message):
    event_name: Literal["TechnologyUpdated"] = Field("TechnologyUpdated", alias="eventName")
    message_type: Literal["update-technology-request"] = Field("update-technology-request", alias="messageType")
    technology_id: str = Field(..., alias="technologyId")
    project_id: str = Field(..., alias="projectId")
    technology_name: str = Field(..., alias="technologyName")
