from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCode(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    productCodeId: str = Field(..., alias="ProductCodeId", title="ProductCodeId")
    productCodeType: Optional[str] = Field(None, alias="ProductCodeType", title="ProductCodeType")


class EbsInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    encrypted: Optional[bool] = Field(None, alias="Encrypted", title="Encrypted")
    kmsKeyId: Optional[str] = Field(None, alias="KmsKeyId", title="KmsKeyId")


class BlockDeviceMapping(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ebs: Optional[EbsInfo] = Field(None, alias="Ebs", title="Ebs")
    deviceName: Optional[str] = Field(None, alias="DeviceName", title="DeviceName")


class AmiDescription(BaseModel):
    amiId: str = Field(..., title="AmiId")
    state: str = Field(..., title="State")
    platform: Optional[str] = Field(None, title="Platform")
    architecture: Optional[str] = Field(None, title="Architecture")
    name: Optional[str] = Field(None, title="Name")
    description: Optional[str] = Field(None, title="Description")
    ownerId: str = Field(..., title="OwnerId")
    region: str = Field(..., title="Region")
    blockDeviceMappings: list[BlockDeviceMapping] = Field(default_factory=list, title="BlockDeviceMappings")
    productCodes: list[ProductCode] = Field(default_factory=list, title="ProductCodes")
