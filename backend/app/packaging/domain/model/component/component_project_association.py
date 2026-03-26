from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ComponentProjectAssociationPrimaryKey(unit_of_work.PrimaryKey):
    componentId: str = Field(..., title="ComponentId")
    projectId: str = Field(..., title="ProjectId")


class ComponentProjectAssociation(unit_of_work.Entity):
    componentId: str = Field(..., title="ComponentId")
    projectId: str = Field(..., title="ProjectId")
