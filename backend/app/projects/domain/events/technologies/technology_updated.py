from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class TechnologyUpdated(message_bus.Message):
    event_name: str = Field("TechnologyUpdated", alias="eventName", const=True)
    message_type: str = Field("update-technology-request", alias="messageType", const=True)
    technology_id: str = Field(..., alias="technologyId")
    project_id: str = Field(..., alias="projectId")
    technology_name: str = Field(..., alias="technologyName")
