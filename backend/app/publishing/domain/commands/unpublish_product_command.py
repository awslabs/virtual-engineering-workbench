from pydantic import ConfigDict

from app.publishing.domain.value_objects import product_id_value_object, project_id_value_object
from app.shared.adapters.message_bus import command_bus


class UnpublishProductCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    model_config = ConfigDict(arbitrary_types_allowed=True)
