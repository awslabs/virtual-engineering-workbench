from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(populate_by_name=True)
