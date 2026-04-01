from pydantic import ConfigDict

from app.projects.domain.value_objects import (
    account_error_message_value_object,
    account_id_value_object,
    project_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class FailProjectAccountOnboarding(command_bus.Command):
    project_id: project_id_value_object.ProjectIdValueObject
    account_id: account_id_value_object.AccountIdValueObject
    error: account_error_message_value_object.AccountErrorMessageValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
