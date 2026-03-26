from typing import Optional

from app.packaging.domain.value_objects.image import (
    image_build_version_arn_value_object,
    image_status_value_object,
    image_upstream_id_value_object,
)
from app.packaging.domain.value_objects.pipeline import pipeline_id_value_object
from app.shared.adapters.message_bus import command_bus


class RegisterImageCommand(command_bus.Command):
    imageBuildVersionArn: image_build_version_arn_value_object.ImageBuildVersionArnValueObject
    imageStatus: image_status_value_object.ImageStatusStatusValueObject
    imageUpstreamId: Optional[image_upstream_id_value_object.ImageUpstreamIdValueObject]
    pipelineId: pipeline_id_value_object.PipelineIdValueObject
