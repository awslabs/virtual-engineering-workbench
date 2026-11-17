import random
import string
from enum import StrEnum
from typing import Optional

from pydantic import Field

from app.shared.adapters.unit_of_work_v2 import unit_of_work


class PortfolioStatus(StrEnum):
    Creating = "CREATING"
    Created = "CREATED"
    Failed = "FAILED"


class PortfolioStage(StrEnum):
    DEV = "DEV"
    QA = "QA"
    PROD = "PROD"


def generate_portfolio_id() -> str:
    return "port-" + "".join((random.choice(string.ascii_lowercase + string.digits) for x in range(8)))


class PortfolioPrimaryKey(unit_of_work.PrimaryKey):
    technologyId: str = Field(..., title="TechnologyId")
    awsAccountId: str = Field(..., title="AwsAccountId")


class Portfolio(unit_of_work.Entity):
    portfolioId: str = Field(default_factory=generate_portfolio_id, title="PortfolioId")
    projectId: str = Field(..., title="ProjectId")
    technologyId: str = Field(..., title="TechnologyId")
    awsAccountId: str = Field(..., title="AwsAccountId")
    accountId: Optional[str] = Field(None, title="AccountId")
    stage: PortfolioStage = Field(..., title="Stage")
    region: str = Field(..., title="Region")
    status: PortfolioStatus = Field(..., title="Status")
    scPortfolioId: Optional[str] = Field(None, title="ScPortfolioId")
    scPortfolioName: Optional[str] = Field(None, title="ScPortfolioName")
    createDate: str = Field(..., title="CreateDate")
    lastUpdateDate: str = Field(..., title="LastUpdateDate")
