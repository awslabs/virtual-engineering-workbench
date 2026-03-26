import random
import string
from typing import Optional

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_project_id() -> str:
    return "proj-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(5)))


class ProjectPrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")


class Project(unit_of_work.Entity):
    projectId: str = Field(default_factory=generate_project_id, title="ProjectId")
    projectName: str = Field(..., title="ProjectName")
    projectDescription: Optional[str] = Field(None, title="ProjectDescription")
    isActive: bool = Field(..., title="IsActive")
    createDate: Optional[str] = Field(None, title="CreateDate")
    lastUpdateDate: Optional[str] = Field(None, title="LastUpdateDate")
