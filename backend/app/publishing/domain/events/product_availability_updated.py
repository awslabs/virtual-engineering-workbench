from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.publishing.domain.model import product
from app.publishing.domain.read_models import component_version_detail
from app.shared.adapters.message_bus import message_bus


class VersionStage(str, Enum):
    DEV = "DEV"
    QA = "QA"
    PROD = "PROD"

    def __str__(self):
        return str(self.value)


class ParameterConstraints(BaseModel):
    allowed_pattern: Optional[str] = Field(None, alias="allowedPattern")
    allowed_values: Optional[List[str]] = Field(None, alias="allowedValues")
    constraint_description: Optional[str] = Field(None, alias="constraintDescription")
    max_length: Optional[str] = Field(None, alias="maxLength")
    max_value: Optional[str] = Field(None, alias="maxValue")
    min_length: Optional[str] = Field(None, alias="minLength")
    min_value: Optional[str] = Field(None, alias="minValue")


class ParameterMetadata(BaseModel):
    label: Optional[str] = Field(None, alias="label")
    option_labels: Optional[Dict[str, str]] = Field(None, alias="optionLabels")
    option_warnings: Optional[Dict[str, str]] = Field(None, alias="optionWarnings")


class VersionParameter(BaseModel):
    default_value: Optional[str] = Field(None, alias="defaultValue")
    description: Optional[str] = Field(None, alias="description")
    is_no_echo: Optional[bool] = Field(None, alias="isNoEcho")
    parameter_constraints: Optional[ParameterConstraints] = Field(None, alias="parameterConstraints")
    parameter_key: str = Field(..., alias="parameterKey")
    parameter_type: Optional[str] = Field(None, alias="parameterType")
    parameter_metadata: Optional[ParameterMetadata] = Field(None, alias="parameterMetadata")
    is_technical_parameter: bool = Field(False, alias="isTechnicalParameter")


class ProductVersionMetadataItem(BaseModel):
    label: Optional[str] = Field(None, title="Label")
    value: Optional[List[str]] = Field(None, title="Value")


class Version(BaseModel):
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    technology_id: str = Field(..., alias="technologyId")
    version_id: str = Field(..., alias="versionId")
    version_name: str = Field(..., alias="versionName")
    version_description: Optional[str] = Field(None, alias="versionDescription")
    aws_account_id: str = Field(..., alias="awsAccountId")
    account_id: str = Field(..., alias="accountId")
    stage: VersionStage = Field(..., alias="stage")
    region: str = Field(..., alias="region")
    ami_id: str = Field(..., alias="amiId")
    sc_product_id: str = Field(..., alias="scProductId")
    sc_provisioning_artifact_id: str = Field(..., alias="scProvisioningArtifactId")
    is_recommended_version: bool = Field(..., alias="isRecommendedVersion")
    parameters: Optional[List[VersionParameter]] = Field(None, alias="parameters")
    metadata: Optional[Dict[str, ProductVersionMetadataItem]] = Field(None, title="metadata")
    componentVersionDetails: list[component_version_detail.ComponentVersionDetail] | None = Field(
        None, title="ComponentVersionDetails"
    )
    osVersion: str | None = Field(None, title="OsVersion")
    last_update_date: str = Field(..., alias="lastUpdateDate")


class ProductAvailabilityUpdated(message_bus.Message):
    event_name: str = Field("ProductAvailabilityUpdated", alias="eventName", const=True)
    project_id: str = Field(..., alias="projectId")
    product_id: str = Field(..., alias="productId")
    product_type: str = Field(..., alias="productType")
    product_name: str = Field(..., alias="productName")
    product_description: str = Field(..., alias="productDescription")
    technology_id: str = Field(..., alias="technologyId")
    technology_name: str = Field(..., alias="technologyName")
    available_stages: List[product.ProductStage] = Field(..., alias="availableStages")
    available_regions: List[str] = Field(..., alias="availableRegions")
    paused_stages: Optional[List[product.ProductStage]] = Field(None, alias="pausedStages")
    paused_regions: Optional[List[str]] = Field(None, alias="pausedRegions")
    last_update_date: str = Field(..., alias="lastUpdateDate")
