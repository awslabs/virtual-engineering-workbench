from decimal import Decimal
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Currency(str, Enum):
    USDollar = "USD"

    def __str__(self):
        return str(self.value)


class CostForecastDetails(BaseModel):
    instanceType: Optional[str] = Field(None, description="Instance type of the product version", title="InstanceType")
    volumeSize: Optional[str] = Field(None, description="Volume size of the product version", title="VolumeSize")
    cost: Decimal = Field(
        ...,
        description="Estimated cost forecast for the product version with given instance type and volume size",
        title="Cost",
    )


class CostForecast(BaseModel):
    productId: str = Field(..., description="Unique ID of the product.", title="ProductId")
    productVersionId: str = Field(..., description="Unique ID of the product version", title="ProductVersionId")
    costForecast: List[CostForecastDetails] = Field(
        ...,
        description="List of cost forecast for the product versions that define the product",
        title="CostForecast",
    )
    intervalValue: Decimal = Field(..., description="Interval value for the cost forecast", title="IntervalValue")
    intervalUnit: str = Field(..., description="Interval unit for the cost forecast", title="IntervalUnit")
    currency: str = Field(..., description="Currency for the cost forecast", title="Currency")


class GetCostForecastResponse(BaseModel):
    costForecasts: List[CostForecast]


class CostForecastForProductDetails(BaseModel):
    minValue: Decimal = Field(..., title="Min")
    maxValue: Decimal = Field(..., title="Max")
    intervalValue: Decimal = Field(..., title="IntervalValue")
    intervalUnit: str = Field(..., title="IntervalUnit")
    currency: Currency = Field(Currency.USDollar, title="Currency")


class CostForecastForProduct(BaseModel):
    costForecastDetails: CostForecastForProductDetails = Field(..., title="Details")
