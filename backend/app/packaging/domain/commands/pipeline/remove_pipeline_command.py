from typing import Optional

from app.packaging.domain.value_objects.pipeline import (
    pipeline_arn_value_object,
    pipeline_distribution_config_arn_value_object,
    pipeline_id_value_object,
    pipeline_infrastructure_config_arn_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object
from app.shared.adapters.message_bus import command_bus


class RemovePipelineCommand(command_bus.Command):
    projectId: project_id_value_object.ProjectIdValueObject
    pipelineId: pipeline_id_value_object.PipelineIdValueObject
    distributionConfigArn: Optional[
        pipeline_distribution_config_arn_value_object.PipelineDistributionConfigArnValueObject
    ]
    infrastructureConfigArn: Optional[
        pipeline_infrastructure_config_arn_value_object.PipelineInfrastructureConfigArnValueObject
    ]
    pipelineArn: Optional[pipeline_arn_value_object.PipelineArnValueObject]
