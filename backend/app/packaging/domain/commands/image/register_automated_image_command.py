from app.packaging.domain.value_objects.image import (
    ami_id_value_object,
    product_id_value_object,
)
from app.packaging.domain.value_objects.pipeline import pipeline_id_value_object
from app.packaging.domain.value_objects.shared import (
    project_id_value_object,
    user_id_value_object,
    version_release_type_value_object,
)
from app.shared.adapters.message_bus import command_bus


class RegisterAutomatedImageCommand(command_bus.Command):
    amiId: ami_id_value_object.AmiIdValueObject
    productId: product_id_value_object.ProductIdValueObject
    projectId: project_id_value_object.ProjectIdValueObject
    pipelineId: pipeline_id_value_object.PipelineIdValueObject
    productVersionReleaseType: version_release_type_value_object.VersionReleaseTypeValueObject
    userId: user_id_value_object.UserIdValueObject
