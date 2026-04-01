from pydantic import BaseModel, ConfigDict, Field


class NetworkRouteTableAssociation(BaseModel):
    subnet_id: str | None = Field(None, alias="SubnetId")
    model_config = ConfigDict(populate_by_name=True)


class NetworkRouteTableRoute(BaseModel):
    gateway_id: str | None = Field(None, alias="GatewayId")
    transit_gateway_id: str | None = Field(None, alias="TransitGatewayId")
    model_config = ConfigDict(populate_by_name=True)


class NetworkRouteTable(BaseModel):
    associations: list[NetworkRouteTableAssociation] = Field(..., alias="Associations")
    routes: list[NetworkRouteTableRoute] = Field(..., alias="Routes")
    model_config = ConfigDict(populate_by_name=True)
