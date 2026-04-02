from pydantic import ConfigDict

from app.projects.domain.value_objects import (
    account_id_value_object,
    account_status_value_object,
    project_id_value_object,
)
from app.shared.adapters.message_bus import command_bus


class ActivateProjectAccountCommand(command_bus.Command):
    account_id: account_id_value_object.AccountIdValueObject
    account_status: account_status_value_object.AccountStatusValueObject
    project_id: project_id_value_object.ProjectIdValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
