import random
import string
from enum import StrEnum
from typing import Optional

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_pipeline_id() -> str:
    return "pipe-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


class PipelineStatus(StrEnum):
    Created = "CREATED"
    Creating = "CREATING"
    Failed = "FAILED"
    Updating = "UPDATING"
    Retired = "RETIRED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, PipelineStatus))


class PipelinePrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")
    pipelineId: str = Field(..., title="PipelineId")


class Pipeline(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    pipelineId: str = Field(default_factory=generate_pipeline_id, title="PipelineId")
    buildInstanceTypes: list[str] = Field(..., title="BuildInstanceTypes")
    pipelineDescription: str = Field(..., title="PipelineDescription")
    pipelineName: str = Field(..., title="PipelineName")
    pipelineSchedule: str = Field(..., title="PipelineSchedule")
    recipeId: str = Field(..., title="RecipeId")
    recipeName: str = Field(..., title="RecipeName")
    recipeVersionId: str = Field(..., title="RecipeVersionId")
    recipeVersionName: str = Field(..., title="RecipeVersionName")
    status: PipelineStatus = Field(..., title="Status")
    productId: Optional[str] = Field(None, title="ProductId")
    distributionConfigArn: Optional[str] = Field(None, title="DistributionConfigArn")
    infrastructureConfigArn: Optional[str] = Field(None, title="InfrastructureConfigArn")
    pipelineArn: Optional[str] = Field(None, title="PipelineArn")
    createDate: str = Field(..., title="CreateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")
