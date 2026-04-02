from typing import Literal

from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class TechnologyDeleted(message_bus.Message):
    event_name: Literal["TechnologyDeleted"] = Field("TechnologyDeleted", alias="eventName")
    technology_id: str = Field(..., alias="technologyId")
    project_id: str = Field(..., alias="projectId")
