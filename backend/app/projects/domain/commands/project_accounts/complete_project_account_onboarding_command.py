from app.projects.domain.value_objects import account_id_value_object, project_id_value_object
from app.shared.adapters.message_bus import command_bus


class CompleteProjectAccountOnboarding(command_bus.Command):
    project_id: project_id_value_object.ProjectIdValueObject
    account_id: account_id_value_object.AccountIdValueObject

    class Config:
        arbitrary_types_allowed = True
