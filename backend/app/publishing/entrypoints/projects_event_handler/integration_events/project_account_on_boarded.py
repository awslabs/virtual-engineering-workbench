from pydantic import BaseModel, Field


class ProjectAccountOnBoarded(BaseModel):
    project_id: str = Field(..., alias="projectId")
    technology_id: str = Field(..., alias="technologyId")
    aws_account_id: str = Field(..., alias="awsAccountId")
    account_id: str = Field(..., alias="accountId")
    account_type: str = Field(..., alias="accountType")
    stage: str = Field(..., alias="stage")
    region: str = Field(..., alias="region")
