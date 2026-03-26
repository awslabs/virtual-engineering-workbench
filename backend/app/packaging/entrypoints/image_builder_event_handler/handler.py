from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source

from app.packaging.domain.commands.image import register_image_command
from app.packaging.domain.model.image import image
from app.packaging.domain.value_objects.image import (
    image_build_version_arn_value_object,
    image_status_value_object,
    image_upstream_id_value_object,
)
from app.packaging.domain.value_objects.pipeline import pipeline_id_value_object
from app.packaging.entrypoints.image_builder_event_handler import bootstrapper, config
from app.packaging.entrypoints.image_builder_event_handler.integration_events import image_builder_pipeline_notification
from app.packaging.entrypoints.image_builder_event_handler.model import image_builder_image_status
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
app = event_handler.EventBridgeEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger, app=app)


@app.handle(
    image_builder_pipeline_notification.ImageBuilderPipelineNotification, event_name="Image Builder SNS notification"
)
def handle_image_builder_pipeline_notification(
    event: image_builder_pipeline_notification.ImageBuilderPipelineNotification,
):
    match event.message.image_status:
        case image_builder_image_status.ImageBuilderImageStatus.Failed:
            logger.warning(
                {
                    "PipelineId": event.message.pipeline_id,
                    "ImageBuildVersionArn": event.message.image_build_version_arn,
                    "ImageStatus": event.message.image_status,
                    "Message": "EC2 Image Builder Pipeline has failed.",
                }
            )
            command = register_image_command.RegisterImageCommand(
                imageBuildVersionArn=image_build_version_arn_value_object.from_str(
                    event.message.image_build_version_arn
                ),
                imageStatus=image_status_value_object.from_str(image.ImageStatus.Failed),
                pipelineId=pipeline_id_value_object.from_str(event.message.pipeline_id),
            )
        case image_builder_image_status.ImageBuilderImageStatus.Available:
            command = register_image_command.RegisterImageCommand(
                imageBuildVersionArn=image_build_version_arn_value_object.from_str(
                    event.message.image_build_version_arn
                ),
                imageStatus=image_status_value_object.from_str(image.ImageStatus.Created),
                imageUpstreamId=image_upstream_id_value_object.from_str(event.message.output_ami_id),
                pipelineId=pipeline_id_value_object.from_str(event.message.pipeline_id),
            )
        case _:
            logger.warning(
                {
                    "PipelineId": event.message.pipeline_id,
                    "ImageBuildVersionArn": event.message.image_build_version_arn,
                    "ImageStatus": event.message.image_status,
                    "Message": "Invalid image status - skipping.",
                }
            )
            return

    dependencies.command_bus.handle(command)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context(log_event=True)  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "ImageBuilderEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: EventBridgeEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
