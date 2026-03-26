from pydantic import BaseModel, Field


class InstanceState(BaseModel):
    name: str = Field(..., alias="Name")


class InstanceTag(BaseModel):
    key: str = Field(..., alias="Key")
    value: str = Field(..., alias="Value")


class InstanceDetails(BaseModel):
    tags: list[InstanceTag] = Field([], alias="Tags")
    private_ip_address: str | None = Field(None, alias="PrivateIpAddress")
    public_ip_address: str | None = Field(None, alias="PublicIpAddress")
    state: InstanceState = Field(..., alias="State")
