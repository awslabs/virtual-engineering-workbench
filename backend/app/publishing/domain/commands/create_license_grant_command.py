from pydantic import ConfigDict

from app.publishing.domain.value_objects import (
    ami_id_value_object,
    aws_account_id_value_object,
    grant_name_value_object,
    project_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class CreateLicenseGrantCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    amiId: ami_id_value_object.AmiIdValueObject
    targetAccountId: aws_account_id_value_object.AWSAccountIDValueObject
    grantName: grant_name_value_object.GrantNameValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
