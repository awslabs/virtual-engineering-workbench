from pydantic import BaseModel, Field


class NetworkSubnetTag(BaseModel):
    key: str = Field(..., alias="Key")
    value: str = Field(..., alias="Value")


class NetworkSubnet(BaseModel):
    availability_zone: str = Field(..., alias="AvailabilityZone")
    available_ip_address_count: int = Field(..., alias="AvailableIpAddressCount")
    subnet_id: str = Field(..., alias="SubnetId")
    tags: list[NetworkSubnetTag] = Field([], alias="Tags")
    cidr_block: str = Field(..., alias="CidrBlock")
    vpc_id: str = Field(..., alias="VpcId")

    class Config:
        allow_population_by_field_name = True
