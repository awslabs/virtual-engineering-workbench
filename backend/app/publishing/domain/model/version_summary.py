from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.publishing.domain.model import version


class VersionSummaryStatus(str, Enum):
    Created = "CREATED"
    Failed = "FAILED"
    Retired = "RETIRED"
    Processing = "PROCESSING"

    def __str__(self):
        return str(self.value)


class VersionSummary(BaseModel):
    versionId: str = Field(..., description="The id of the version", title="VersionId")
    name: str = Field(..., description="The version number", title="Name")
    description: Optional[str] = Field(None, description="The description for the version", title="Description")
    versionType: str = Field(
        ..., description="The version type (RELEASE_CANDIDATE|RELEASED|RESTORED)", title="VersionType"
    )
    stages: List[version.VersionStage] = Field(..., title="Stages")
    status: VersionSummaryStatus = Field(
        ..., description="Status of the version summary (CREATED|FAILED|RETIRED|PROCESSING).", title="status"
    )
    recommendedVersion: bool = Field(
        ...,
        description="The recommended version for the product user should use",
        title="RecommendedVersion",
    )
    lastUpdate: str = Field(
        ...,
        description="Timestamp of when the last change happend to the version",
        title="LastUpdate",
    )
    lastUpdatedBy: str = Field(
        ...,
        description="User ID of the person who last changed the version",
        title="LastUpdatedBy",
    )
    restoredFromVersionName: Optional[str] = Field(
        None,
        description="Name of the version that this version is restored from, if it is restored",
        title="RestoredFromVersionName",
    )
    originalAmiId: Optional[str] = Field(
        None,
        description="AMI ID of the original image",
        title="OriginalAmiId",
    )
