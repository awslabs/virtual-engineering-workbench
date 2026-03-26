from enum import Enum
from typing import Optional

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class ProductStatus(str, Enum):
    Creating = "CREATING"
    Created = "CREATED"
    Failed = "FAILED"
    Paused = "PAUSED"
    Archiving = "ARCHIVING"
    Archived = "ARCHIVED"

    def __str__(self):
        return str(self.value)


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
    status: ProductStatus = Field(..., title="Status")
    productName: str = Field(..., title="ProductName")
    productType: ProductType = Field(..., title="ProductType")
    productDescription: Optional[str] = Field(None, title="ProductDescription")
    recommendedVersionId: Optional[str] = Field(None, title="RecommendedVersionId")
    availableStages: Optional[list[ProductStage]] = Field(None, title="AvailableStages")
    availableRegions: Optional[list[str]] = Field(None, title="AvailableRegions")
    pausedStages: Optional[list[ProductStage]] = Field(None, title="PausedStages")
    pausedRegions: Optional[list[str]] = Field(None, title="PausedRegions")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
    createdBy: str = Field(..., title="CreatedBy")
    lastUpdatedBy: str = Field(..., title="LastUpdatedBy")


PRODUCT_CONTAINER_TYPES = [ProductType.Container]
PRODUCT_INSTANCE_TYPES = [
    ProductType.VirtualTarget,
    ProductType.Workbench,
]
