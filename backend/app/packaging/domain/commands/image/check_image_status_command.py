from app.packaging.domain.value_objects.image import image_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class CheckImageStatusCommand(command_bus.Command):
    imageId: image_id_value_object.ImageIdValueObject
    projectId: project_id_value_object.ProjectIdValueObject
