from pydantic import ConfigDict

from app.publishing.domain.value_objects import (
    aws_account_id_value_object,
    grant_arn_value_object,
    grant_id_value_object,
    project_id_value_object,
    region_value_object,
)
from app.shared.adapters.message_bus import command_bus


class AcceptLicenseGrantCommand(command_bus.Command):
    grantId: grant_id_value_object.GrantIdValueObject
    grantArn: grant_arn_value_object.GrantArnValueObject
    projectId: project_id_value_object.ProjectIdValueObject
    homeRegion: region_value_object.RegionValueObject
    targetAccountId: aws_account_id_value_object.AWSAccountIDValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
