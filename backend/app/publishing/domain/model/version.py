import random
import string
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.publishing.domain.read_models import component_version_detail
from app.shared.adapters.unit_of_work_v2 import unit_of_work


def generate_version_id() -> str:
    return "vers-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


class VersionReleaseType(str, Enum):
    Major = "MAJOR"
    Minor = "MINOR"
    Patch = "PATCH"

    def __str__(self):
        return str(self.value)

    @staticmethod
    def list():
        return list(map(lambda v: v.value, VersionReleaseType))


class VersionStatus(str, Enum):
    Creating = "CREATING"
    Created = "CREATED"
    Failed = "FAILED"
    Retiring = "RETIRING"
    Retired = "RETIRED"
    Restoring = "RESTORING"
    Updating = "UPDATING"

    def __str__(self):
        return str(self.value)

    @staticmethod
    def list():
        return list(map(lambda v: v.value, VersionStatus))

    @staticmethod
    def get_processing_statuses():
        return [
            str(VersionStatus.Creating),
            str(VersionStatus.Retiring),
            str(VersionStatus.Restoring),
            str(VersionStatus.Updating),
        ]

    @staticmethod
    def get_terminal_statuses():
        return [VersionStatus.Created, VersionStatus.Failed, VersionStatus.Retired]


class VersionStage(str, Enum):
    DEV = "DEV"
    QA = "QA"
    PROD = "PROD"

    def __str__(self):
        return str(self.value)


class VersionType(Enum):
    ReleaseCandidate = ("RELEASE_CANDIDATE", "-rc.", "-rc.{}")
    Restored = ("RESTORED", "-restored.", "-restored.{}")
    Released = ("RELEASED", "", "")

    def __init__(self, text: str, suffix: str, suffix_format: str):
        self.text = text
        self.suffix = suffix
        self.suffix_format = suffix_format


def format_version_name(
    major: str, minor: str, patch: str, version_type: VersionType = VersionType.Released, counter: str = ""
) -> str:
    return f"{major}.{minor}.{patch}{version_type.suffix_format.format(counter)}"


def format_version_name_from_root(
    version_name_root: str, version_type: VersionType = VersionType.Released, counter: str = ""
) -> str:
    return f"{version_name_root}{version_type.suffix_format.format(counter)}"


class ParameterConstraints(BaseModel):
    allowedPattern: Optional[str] = Field(None, title="AllowedPattern")
    allowedValues: Optional[List[str]] = Field(None, title="AllowedValues")
    constraintDescription: Optional[str] = Field(None, title="ConstraintDescription")
    maxLength: Optional[str] = Field(None, title="MaxLength")
    maxValue: Optional[str] = Field(None, title="MaxValue")
    minLength: Optional[str] = Field(None, title="MinLength")
    minValue: Optional[str] = Field(None, title="MinValue")


class ParameterMetadata(BaseModel):
    label: Optional[str] = Field(None, title="Label")
    optionLabels: Optional[Dict[str, str]] = Field(None, title="OptionLabels")
    optionWarnings: Optional[Dict[str, str]] = Field(None, title="OptionWarnings")


class VersionParameter(BaseModel):
    defaultValue: Optional[str] = Field(None, title="DefaultValue")
    description: Optional[str] = Field(None, title="Description")
    isNoEcho: Optional[bool] = Field(None, title="IsNoEcho")
    parameterConstraints: Optional[ParameterConstraints] = Field(None, title="ParameterConstraints")
    parameterKey: str = Field(..., title="ParameterKey")
    parameterType: Optional[str] = Field(None, title="ParameterType")
    parameterMetadata: Optional[ParameterMetadata] = Field(None, title="ParameterMetadata")
    isTechnicalParameter: bool = Field(False, title="IsTechnicalParameter")


class ProductVersionMetadataItem(BaseModel):
    label: Optional[str] = Field(None, title="Label")
    value: Optional[List[str]] = Field(None, title="Value")


class VersionPrimaryKey(unit_of_work.PrimaryKey):
    productId: str = Field(..., title="ProductId")
    versionId: str = Field(..., title="versionId")
    awsAccountId: str = Field(..., title="AwsAccountId")


class Version(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    productId: str = Field(..., title="ProductId")
    technologyId: str = Field(..., title="TechnologyId")
    versionId: str = Field(..., title="VersionId")
    versionName: str = Field(..., title="VersionName")
    versionDescription: Optional[str] = Field(None, title="VersionDescription")
    versionType: str = Field(..., title="VersionType")
    awsAccountId: str = Field(..., title="AwsAccountId")
    accountId: Optional[str] = Field(None, title="AccountId")
    stage: VersionStage = Field(..., title="Stage")
    region: str = Field(..., title="Region")
    originalAmiId: Optional[str] = Field(None, title="OriginalAmiId")
    copiedAmiId: Optional[str] = Field(None, title="CopiedAmiId")
    imageTag: Optional[str] = Field(None, title="ImageTag")
    imageDigest: Optional[str] = Field(None, title="ImageDigest")
    status: VersionStatus = Field(..., title="status")
    scPortfolioId: str = Field(..., title="ScPortfolioId")
    scProductId: Optional[str] = Field(None, title="ScProductId")
    scProvisioningArtifactId: Optional[str] = Field(None, title="ScProvisioningArtifactId")
    isRecommendedVersion: bool = Field(..., title="IsRecommendedVersion")
    draftTemplateLocation: Optional[str] = Field(None, title="DraftTemplateLocation")
    templateLocation: Optional[str] = Field(None, title="TemplateLocation")
    retireReason: Optional[str] = Field(None, title="RetireReason")
    restoredFromVersionName: Optional[str] = Field(None, title="RestoredFromVersionName")
    parameters: Optional[List[VersionParameter]] = Field(None, title="Parameters")
    metadata: Optional[Dict[str, ProductVersionMetadataItem]] = Field(None, title="Metadata")
    componentVersionDetails: list[component_version_detail.ComponentVersionDetail] | None = Field(
        None, title="ComponentVersionDetails"
    )
    osVersion: str | None = Field(None, title="OsVersion")
    platform: str | None = Field(None, title="platform")
    architecture: str | None = Field(None, title="architecture")
    integrations: list[str] = Field([], title="integrations")
    createDate: str = Field(..., title="createDate")
    lastUpdateDate: str = Field(..., title="lastUpdateDate")
    createdBy: str = Field(..., title="createdBy")
    lastUpdatedBy: str = Field(..., title="lastUpdatedBy")
