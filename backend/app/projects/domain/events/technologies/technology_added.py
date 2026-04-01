from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class TechnologyAdded(message_bus.Message):
    event_name: Literal["TechnologyAdded"] = Field("TechnologyAdded", alias="eventName")
    message_type: Literal["add-technology-request"] = Field("add-technology-request", alias="messageType")
    technology_id: str = Field(..., alias="technologyId")
    project_id: str = Field(..., alias="projectId")
    technology_name: str = Field(..., alias="technologyName")
