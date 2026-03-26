from pydantic import BaseModel, Field


class PrivateIpAddress(BaseModel):
    private_ip_address: str = Field(..., alias="PrivateIpAddress")


class NetworkInterface(BaseModel):
    network_interface_id: str = Field(..., alias="NetworkInterfaceId")
    private_ip_addresses: list[PrivateIpAddress] = Field(..., alias="PrivateIpAddresses")
