from enum import Enum
from typing import Optional

from pydantic import Field

from app.provisioning.domain.read_models import cost_forecast
from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ProductType(str, Enum):
    Workbench = "WORKBENCH"
    VirtualTarget = "VIRTUAL_TARGET"
    Container = "CONTAINER"

    def __str__(self):
        return str(self.value)

    @staticmethod
    def list():
        return list(map(lambda p: p.value, ProductType))


class ProductStage(str, Enum):
    DEV = "DEV"
    QA = "QA"
    PROD = "PROD"

    def __str__(self):
        return str(self.value)


class ProductPrimaryKey(unit_of_work.PrimaryKey):
    projectId: str = Field(..., title="ProjectId")
    productId: str = Field(..., title="ProductId")


class Product(unit_of_work.Entity):
    projectId: str = Field(..., title="ProjectId")
    productId: str = Field(..., title="ProductId")
    technologyId: str = Field(..., title="TechnologyId")
    technologyName: str = Field(..., title="TechnologyName")
    productName: str = Field(..., title="ProductName")
    productType: ProductType = Field(..., title="ProductType")
    productDescription: Optional[str] = Field(None, title="ProductDescription")
    availableStages: Optional[list[ProductStage]] = Field(None, title="AvailableStages")
    availableRegions: Optional[list[str]] = Field(None, title="AvailableRegions")
    pausedStages: Optional[list[ProductStage]] = Field(None, title="PausedStages")
    pausedRegions: Optional[list[str]] = Field(None, title="PausedRegions")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    averageProvisioningTime: Optional[int] = Field(None, title="AverageProvisioningTime")
    totalReportedTimes: Optional[int] = Field(None, title="TotalReportedTimes")
    availableTools: set[str] | None = Field(None, title="AvailableTools")
    availableOSVersions: set[str] | None = Field(None, title="AvailableOSVersions")
    costForecastDetails: Optional[cost_forecast.CostForecastForProductDetails] = Field(
        None, title="CostForecastDetails"
    )
