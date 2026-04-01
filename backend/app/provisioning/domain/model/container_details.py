from pydantic import BaseModel, ConfigDict, Field


class ContainerState(BaseModel):
    name: str = Field(..., alias="Name")


class ContainerTag(BaseModel):
    key: str = Field(..., alias="Key")
    value: str = Field(..., alias="Value")
    model_config = ConfigDict(populate_by_name=True)


class ContainerDetails(BaseModel):
    tags: list[ContainerTag] = Field([], alias="Tags")
    private_ip_address: str | None = Field(None, alias="PrivateIpAddress")
    state: ContainerState = Field(..., alias="State")
    task_arn: str | None = Field(None, alias="TaskArn")
    name: str | None = Field(None, alias="Name")
    model_config = ConfigDict(populate_by_name=True)
