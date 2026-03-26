from typing import Optional

from pydantic import BaseModel, Field


class Project(BaseModel):
    projectId: str = Field(..., title="ProjectId")
    projectName: Optional[str] = Field(None, title="ProjectName")
    projectDescription: Optional[str] = Field(None, title="ProjectDescription")
