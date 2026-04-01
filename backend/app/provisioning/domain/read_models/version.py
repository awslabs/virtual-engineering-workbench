from enum import StrEnum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.provisioning.domain.read_models import component_version_detail
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class VersionStage(StrEnum):
    DEV = "DEV"
    QA = "QA"
    PROD = "PROD"


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
    parameterMetaData: Optional[ParameterMetadata] = Field(None, title="ParameterMetadata", alias="parameterMetadata")
    isTechnicalParameter: bool = Field(False, title="IsTechnicalParameter")
    model_config = ConfigDict(populate_by_name=True)


class ProductVersionMetadataItem(BaseModel):
    label: Optional[str] = Field(None, title="Label")
    value: Optional[List[str]] = Field(None, title="Value")


class VersionPrimaryKey(unit_of_work.PrimaryKey):
    productId: str = Field(..., title="ProductId")
    versionId: str = Field(..., title="VersionId")
    awsAccountId: str = Field(..., title="AwsAccountId")


class Version(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    productId: str = Field(..., title="ProductId")
    technologyId: str = Field(..., title="TechnologyId")
    versionId: str = Field(..., title="VersionId")
    versionName: str = Field(..., title="VersionName")
    versionDescription: Optional[str] = Field(None, title="VersionDescription")
    awsAccountId: str = Field(..., title="AwsAccountId")
    accountId: str = Field(..., title="AccountId")
    stage: VersionStage = Field(..., title="Stage")
    region: str = Field(..., title="Region")
    amiId: Optional[str] = Field(None, title="AmiId")
    scProductId: str = Field(..., title="ScProductId")
    scProvisioningArtifactId: str = Field(..., title="ScProvisioningArtifactId")
    isRecommendedVersion: bool = Field(..., title="IsRecommendedVersion")
    parameters: Optional[List[VersionParameter]] = Field(None, title="Parameters")
    metadata: Optional[Dict[str, ProductVersionMetadataItem]] = Field(None, title="Metadata")
    componentVersionDetails: list[component_version_detail.ComponentVersionDetail] | None = Field(
        None, title="ComponentVersionDetails"
    )
    osVersion: str | None = Field(None, title="OsVersion")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")


class GetAvailableProductVersionsInternalResponse(BaseModel):
    availableProductVersions: Optional[List[Version]] = Field(None, title="AvailableProductVersions")


class GetProductVersionInternalResponse(BaseModel):
    version: Optional[Version] = Field(None, title="Version")
