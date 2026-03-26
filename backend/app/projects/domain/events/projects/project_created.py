from pydantic import Field

from app.shared.adapters.message_bus import message_bus


class ProjectCreated(message_bus.Message):
    event_name: str = Field("ProjectCreated", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    project_name: str = Field(..., alias="projectName")
    project_description: str = Field(..., alias="projectDescription")
    is_active: bool = Field(..., alias="isActive")
