import random
import string
from enum import StrEnum
from typing import Optional

from pydantic import Field

from app.packaging.domain.model.image.image_constants import ImageSource
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_image_id() -> str:
    return "image-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


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
    imageBuildVersion: Optional[int] = Field(None, title="ImageBuildVersion")
    imageBuildVersionArn: Optional[str] = Field(None, title="ImageBuildVersionArn")
    pipelineId: Optional[str] = Field(None, title="PipelineId")
    pipelineName: Optional[str] = Field(None, title="PipelineName")
    recipeId: Optional[str] = Field(None, title="RecipeId")
    recipeName: Optional[str] = Field(None, title="RecipeName")
    recipeVersionId: Optional[str] = Field(None, title="RecipeVersionId")
    recipeVersionName: Optional[str] = Field(None, title="RecipeVersionName")
    status: ImageStatus = Field(..., title="Status")
    imageUpstreamId: Optional[str] = Field(None, title="ImageUpstreamId")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    imageSource: ImageSource = Field(ImageSource.PIPELINE, title="ImageSource")
    imageName: Optional[str] = Field(None, title="ImageName")
    imageDescription: Optional[str] = Field(None, title="ImageDescription")
    platform: Optional[str] = Field(None, title="Platform")
    architecture: Optional[str] = Field(None, title="Architecture")
    osVersion: Optional[str] = Field(None, title="OsVersion")
    componentVersionDetails: list[dict] = Field(default_factory=list, title="ComponentVersionDetails")
    marketplaceMetadata: Optional[dict] = Field(None, title="MarketplaceMetadata")
    sourceAccountId: Optional[str] = Field(None, title="SourceAccountId")
    originalAmiRegion: Optional[str] = Field(None, title="OriginalAmiRegion")
    encryptionType: Optional[str] = Field(None, title="EncryptionType")
    kmsKeyId: Optional[str] = Field(None, title="KmsKeyId")
    importValidatedAt: Optional[str] = Field(None, title="ImportValidatedAt")
