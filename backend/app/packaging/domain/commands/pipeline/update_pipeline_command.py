from typing import Optional

from app.packaging.domain.value_objects.image import product_id_value_object
from app.packaging.domain.value_objects.pipeline import (
    pipeline_build_instance_types_value_object,
    pipeline_id_value_object,
    pipeline_schedule_value_object,
)
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class UpdatePipelineCommand(command_bus.Command):
    pipelineId: pipeline_id_value_object.PipelineIdValueObject
    projectId: project_id_value_object.ProjectIdValueObject
    buildInstanceTypes: Optional[pipeline_build_instance_types_value_object.PipelineBuildInstanceTypesValueObject]
    pipelineSchedule: Optional[pipeline_schedule_value_object.PipelineScheduleValueObject]
    recipeVersionId: Optional[recipe_version_id_value_object.RecipeVersionIdValueObject]
    productId: Optional[product_id_value_object.ProductIdValueObject] = None
    lastUpdatedBy: user_id_value_object.UserIdValueObject
