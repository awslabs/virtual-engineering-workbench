from pydantic import BaseModel, Field


class NetworkRouteTableAssociation(BaseModel):
    subnet_id: str | None = Field(None, alias="SubnetId")

    class Config:
        allow_population_by_field_name = True


class NetworkRouteTableRoute(BaseModel):
    gateway_id: str | None = Field(None, alias="GatewayId")
    transit_gateway_id: str | None = Field(None, alias="TransitGatewayId")

    class Config:
        allow_population_by_field_name = True


class NetworkRouteTable(BaseModel):
    associations: list[NetworkRouteTableAssociation] = Field(..., alias="Associations")
    routes: list[NetworkRouteTableRoute] = Field(..., alias="Routes")

    class Config:
        allow_population_by_field_name = True
