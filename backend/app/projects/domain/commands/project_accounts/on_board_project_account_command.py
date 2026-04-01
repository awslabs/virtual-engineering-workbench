from pydantic import ConfigDict

from app.projects.domain.model import project_account
from app.projects.domain.value_objects import (
    account_description_value_object,
    account_name_value_object,
    account_technology_id_value_object,
    account_type_value_object,
    aws_account_id_value_object,
    project_id_value_object,
    region_value_object,
)
from app.shared.adapters.message_bus import command_bus


class OnBoardProjectAccountCommand(command_bus.Command):
    account_id: aws_account_id_value_object.AWSAccountIDValueObject
    account_type: account_type_value_object.AccountTypeValueObject
    account_name: account_name_value_object.AccountNameValueObject
    account_description: account_description_value_object.AccountDescriptionValueObject
    project_id: project_id_value_object.ProjectIdValueObject
    stage: project_account.ProjectAccountStageEnum
    technology: account_technology_id_value_object.AccountTechnologyIdValueObject
    region: region_value_object.RegionValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
