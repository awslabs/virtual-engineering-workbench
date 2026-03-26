from typing import Optional

from app.packaging.domain.value_objects.image import product_id_value_object
from app.packaging.domain.value_objects.pipeline import (
    pipeline_build_instance_types_value_object,
    pipeline_description_value_object,
    pipeline_name_value_object,
    pipeline_schedule_value_object,
)
from app.packaging.domain.value_objects.recipe import recipe_id_value_object
from app.packaging.domain.value_objects.recipe_version import recipe_version_id_value_object
from app.packaging.domain.value_objects.shared import project_id_value_object, user_id_value_object
from app.shared.adapters.message_bus import command_bus


class CreatePipelineCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    buildInstanceTypes: pipeline_build_instance_types_value_object.PipelineBuildInstanceTypesValueObject
    pipelineDescription: pipeline_description_value_object.PipelineDescriptionValueObject
    pipelineName: pipeline_name_value_object.PipelineNameValueObject
    pipelineSchedule: pipeline_schedule_value_object.PipelineScheduleValueObject
    recipeId: recipe_id_value_object.RecipeIdValueObject
    recipeVersionId: recipe_version_id_value_object.RecipeVersionIdValueObject
    createdBy: user_id_value_object.UserIdValueObject
    productId: Optional[product_id_value_object.ProductIdValueObject] = None
