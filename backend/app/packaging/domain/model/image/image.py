import random
import string
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_image_id() -> str:
    return "image-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


class ImageMetadata(BaseModel):
    image_build_version_arn: str
    snapshot_ids: list[str]


class ImageStatus(StrEnum):
    Created = "CREATED"
    Creating = "CREATING"
    Failed = "FAILED"
    Retired = "RETIRED"
    Deleted = "DELETED"

    @staticmethod
    def list():
        return list(map(lambda v: v.value, ImageStatus))


class ImagePrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")
    imageId: str = Field(..., title="ImageId")


class Image(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    imageId: str = Field(default_factory=generate_image_id, title="ImageId")
    imageBuildVersion: int = Field(..., title="ImageBuildVersion")
    imageBuildVersionArn: str = Field(..., title="ImageBuildVersionArn")
    pipelineId: str = Field(..., title="PipelineId")
    pipelineName: str = Field(..., title="PipelineName")
    recipeId: str = Field(..., title="RecipeId")
    recipeName: str = Field(..., title="RecipeName")
    recipeVersionId: str = Field(..., title="RecipeVersionId")
    recipeVersionName: str = Field(..., title="RecipeVersionName")
    status: ImageStatus = Field(..., title="Status")
    imageUpstreamId: Optional[str] = Field(None, title="ImageUpstreamId")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
