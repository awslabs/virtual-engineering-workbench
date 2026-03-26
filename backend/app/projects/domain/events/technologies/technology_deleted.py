from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class TechnologyDeleted(message_bus.Message):
    event_name: str = Field("TechnologyDeleted", alias="eventName", const=True)
    technology_id: str = Field(..., alias="technologyId")
    project_id: str = Field(..., alias="projectId")
