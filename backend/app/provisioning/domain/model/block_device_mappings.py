from pydantic import BaseModel, Field


class BlockDevice(BaseModel):
    deviceName: str = Field(..., title="Device name")
    volumeId: str = Field(..., title="Volume ID")


class BlockDeviceMappings(BaseModel):
    rootDeviceName: str = Field(..., title="Root Device Name")
    mappings: list[BlockDevice] = Field(..., title="Mappings")
