from typing import Optional

from pydantic import ConfigDict

from app.projects.domain.value_objects import aws_account_id_value_object, region_value_object, variables_value_object
from app.shared.adapters.message_bus import command_bus


class SetupPrerequisitesResourcesCommand(command_bus.Command):
    aws_account_id: aws_account_id_value_object.AWSAccountIDValueObject
    region: region_value_object.RegionValueObject
    variables: Optional[variables_value_object.VariablesValueObject] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
