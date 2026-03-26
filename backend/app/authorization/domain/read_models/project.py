from pydantic import BaseModel, Field


class Project(BaseModel):
    projectId: str = Field(..., title="ProjectId")
