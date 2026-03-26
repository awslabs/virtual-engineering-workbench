from pydantic import BaseModel

from app.publishing.domain.value_objects import (
    account_id_value_object,
    aws_account_id_value_object,
    project_id_value_object,
    region_value_object,
    stage_value_object,
    tech_id_value_object,
)


class CreatePortfolioCommand(BaseModel):
    projectId: project_id_value_object.ProjectIdValueObject
    technologyId: tech_id_value_object.TechIdValueObject
    awsAccountId: aws_account_id_value_object.AWSAccountIDValueObject
    accountId: account_id_value_object.AccountIdValueObject
    stage: stage_value_object.StageValueObject
    region: region_value_object.RegionValueObject

    class Config:
        arbitrary_types_allowed = True
