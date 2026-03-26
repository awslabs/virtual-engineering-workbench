from app.publishing.domain.value_objects import product_id_value_object, project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class ArchiveProductCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    archivedBy: user_id_value_object.UserIdValueObject
