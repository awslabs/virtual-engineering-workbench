import random
import string
from typing import Optional

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_id():
    return uuid_to_str


def uuid_to_str():
    tech_id = "tech-"
    for _ in range(5):
        tech_id += random.choice(string.ascii_lowercase)
    return tech_id


class TechnologyPrimaryKey(unit_of_work.PrimaryKey):
    id: str = Field(..., title="Id")
    project_id: str = Field(..., title="ProjectId")


class Technology(unit_of_work.Entity):
    id: str = Field(default_factory=generate_id(), title="Id")
    project_id: str | None = Field(None, title="ProjectId")
    name: str = Field(..., title="Name")
    description: Optional[str] = Field(None, title="Description")
    createDate: Optional[str] = Field(None, title="CreateDate")
    lastUpdateDate: Optional[str] = Field(None, title="LastUpdateDate")
