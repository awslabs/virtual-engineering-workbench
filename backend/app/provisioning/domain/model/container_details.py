from pydantic import BaseModel, Field


class ContainerState(BaseModel):
    name: str = Field(..., alias="Name")


class ContainerTag(BaseModel):
    key: str = Field(..., alias="Key")
    value: str = Field(..., alias="Value")

    class Config:
        allow_population_by_field_name = True


class ContainerDetails(BaseModel):
    tags: list[ContainerTag] = Field([], alias="Tags")
    private_ip_address: str | None = Field(None, alias="PrivateIpAddress")
    state: ContainerState = Field(..., alias="State")
    task_arn: str | None = Field(None, alias="TaskArn")
    name: str | None = Field(None, alias="Name")

    class Config:
        allow_population_by_field_name = True
