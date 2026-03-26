from enum import StrEnum
from typing import Optional

from pydantic import Field

from app.provisioning.domain.model import (
    additional_configuration,
    block_device_mappings,
    product_status,
    provisioned_product_output,
    provisioning_parameter,
)
from app.provisioning.domain.read_models.component_version_detail import (
    ComponentVersionDetail,
)
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class InstanceResourceRecommendationEnum(StrEnum):
    CPUOverProvisioned = "CPU_OVER_PROVISIONED"
    CPUUnderProvisioned = "CPU_UNDER_PROVISIONED"
    MemoryOverProvisioned = "MEMORY_OVER_PROVISIONED"
    MemoryUnderProvisioned = "MEMORY_UNDER_PROVISIONED"


class InstanceRecommendationReasonEnum(StrEnum):
    OverProvisioned = "OVER_PROVISIONED"
    UnderProvisioned = "UNDER_PROVISIONED"


class InstancePlatform(StrEnum):
    Windows = "Windows"
    Linux = "Linux"


class ProvisionedProductType(StrEnum):
    Workbench = "WORKBENCH"
    VirtualTarget = "VIRTUAL_TARGET"
    Container = "CONTAINER"

    @staticmethod
    def list():
        return list(map(lambda p: p.value, ProvisionedProductType))


class ProvisionedProductStage(StrEnum):
    DEV = "DEV"
    QA = "QA"
    PROD = "PROD"


class ExperimentalEnum(StrEnum):
    TRUE = "True"
    FALSE = "False"


class DeploymentOption(StrEnum):
    SINGLE_AZ = "SINGLE_AZ"
    MULTI_AZ = "MULTI_AZ"

    @staticmethod
    def list():
        return list(map(lambda d: d.value, DeploymentOption))


class ProvisionedProductPrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")
    provisionedProductId: str = Field(..., title="ProvisionedProductId")


class ProvisionedProduct(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    provisionedProductId: str = Field(..., title="ProvisionedProductId")
    provisionedProductName: str = Field(..., title="ProvisionedProductName")
    provisionedProductType: ProvisionedProductType = Field(..., title="ProvisionedProductType")
    userId: str = Field(..., title="UserId")
    userDomains: list[str] = Field(..., title="UserDomains")
    status: product_status.ProductStatus = Field(..., title="Status")
    statusReason: str | None = Field(None, title="StatusReason")
    productId: str = Field(..., title="ProductId")
    productName: str = Field(..., title="ProductName")
    productDescription: Optional[str] = Field(None, title="ProductDescription")
    technologyId: str = Field(..., title="TechnologyId")
    versionId: str = Field(..., title="VersionId")
    versionName: str = Field(..., title="VersionName")
    versionDescription: Optional[str] = Field(None, title="VersionDescription")
    awsAccountId: str = Field(..., title="AwsAccountId")
    accountId: str = Field(..., title="AccountId")
    stage: ProvisionedProductStage = Field(..., title="Stage")
    region: str = Field(..., title="Region")
    amiId: Optional[str] = Field(None, title="AmiId")
    containerClusterName: Optional[str] = Field(None, title="ContainerClusterName")
    containerServiceName: Optional[str] = Field(None, title="ContainerServiceName")
    containerName: Optional[str] = Field(None, title="ContainerName")
    containerTaskArn: Optional[str] = Field(None, title="ContainerTaskArn")
    scProductId: str = Field(..., title="ScProductId")
    scProvisioningArtifactId: str = Field(..., title="ScProvisioningArtifactId")
    scProvisionedProductId: str | None = Field(None, title="ScProvisionedProductId")
    provisioningParameters: Optional[list[provisioning_parameter.ProvisioningParameter]] = Field(
        None, title="provisioningParameters"
    )
    outputs: Optional[list[provisioned_product_output.ProvisionedProductOutput]] = Field(None, title="outputs")
    instanceId: Optional[str] = Field(None, title="InstanceId")
    oldInstanceId: Optional[str] = Field(None, title="OldInstanceId")
    privateIp: Optional[str] = Field(None, title="PrivateIP")
    publicIp: Optional[str] = Field(None, title="PublicIP")
    sshKeyPath: Optional[str] = Field(None, title="SSHKeyPath")
    keyPairId: Optional[str] = Field(None, title="KeyPairId")
    userCredentialName: Optional[str] = Field(None, title="UserCredentialName")
    upgradeAvailable: Optional[bool] = Field(None, title="UpgradeAvailable")
    newVersionName: Optional[str] = Field(None, title="NewVersionName")
    newVersionId: Optional[str] = Field(None, title="NewVersionId")
    newProvisioningParameters: Optional[list[provisioning_parameter.ProvisioningParameter]] = Field(
        None, title="newProvisioningParameters"
    )
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")
    instanceRecommendationReason: Optional[str] = Field(None, title="InstanceRecommendationReason")
    recommendedInstanceType: Optional[str] = Field(None, title="RecommendedInstanceType")
    additionalConfigurations: Optional[list[additional_configuration.AdditionalConfiguration]] = Field(
        None, title="AdditionalConfigurations"
    )
    experimental: Optional[bool] = Field(None, title="Experimental")
    componentVersionDetails: list[ComponentVersionDetail] | None = Field(None, title="ComponentVersionDetails")
    osVersion: str | None = Field(None, title="OsVersion")
    blockDeviceMappings: Optional[block_device_mappings.BlockDeviceMappings] = Field(None, title="BlockDeviceMappings")
    availabilityZonesTriggered: Optional[list[str]] = Field(None, title="AvailabilityZonesTriggered")
    userIpAddress: Optional[str] = Field(None, title="UserIpAddress")
    provisionedCompoundProductId: Optional[str] = Field(None, title="ProvisionedCompoundProductId")
    startDate: Optional[str] = Field(None, title="StartDate")
    isRetired: bool = Field(False, title="IsRetired")
    deploymentOption: str | None = Field(None, title="DeploymentOption")


PRODUCT_CONTAINER_TYPES = [ProvisionedProductType.Container]
PRODUCT_INSTANCE_TYPES = [
    ProvisionedProductType.VirtualTarget,
    ProvisionedProductType.Workbench,
]
