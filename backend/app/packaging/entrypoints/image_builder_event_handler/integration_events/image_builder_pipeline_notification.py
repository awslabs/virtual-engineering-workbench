import json

from pydantic import BaseModel, Field, root_validator, validator

from app.packaging.entrypoints.image_builder_event_handler.model import image_builder_image_status
from app.shared.middleware import event_handler


class ImageBuilderPipelineNotificationBody(BaseModel):
    """
    Please refer to following doc for the SNS notification payload:
    https://docs.aws.amazon.com/imagebuilder/latest/userguide/integ-sns.html
    """

    pipeline_id: str = Field(..., alias="PipelineId")
    image_build_version_arn: str = Field(..., alias="ImageBuildVersionArn")
    image_status: str = Field(..., alias="ImageStatus")
    output_ami_id: str = Field(..., alias="OutputAmiId")

    @root_validator(pre=True)
    def parse_image_builder_pipeline_notification(cls, values) -> dict:
        processed_values = {}
        processed_values["PipelineId"] = values.get("sourcePipelineArn").split("/")[1]
        processed_values["ImageStatus"] = values.get("state").get("status")
        processed_values["ImageBuildVersionArn"] = values.get("arn")
        # Assuming that only one AMI per pipeline is generated
        processed_values["OutputAmiId"] = ""
        if processed_values["ImageStatus"] == image_builder_image_status.ImageBuilderImageStatus.Available:
            processed_values["OutputAmiId"] = values.get("outputResources").get("amis")[0].get("image")

        return processed_values


class ImageBuilderPipelineNotification(event_handler.EventBase):
    message: ImageBuilderPipelineNotificationBody = Field(..., alias="Message")

    @validator("message", pre=True)
    def message_validator(cls, v):
        return ImageBuilderPipelineNotificationBody.parse_obj(json.loads(v))
