from datetime import datetime, timezone

from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source

from app.publishing.domain.read_models import ami, component_version_detail
from app.publishing.domain.value_objects import ami_id_value_object
from app.publishing.entrypoints.packaging_event_handler import bootstrapper, config
from app.publishing.entrypoints.packaging_event_handler.integration_events import (
    automated_image_registration_completed,
    image_deregistered,
    image_imported,
    image_registration_completed,
)
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
metrics_handler = metrics.Metrics()
app_config = config.AppConfig()
dependencies = bootstrapper.bootstrap(app_config, logger)
app = event_handler.EventBridgeEventResolver(logger=logger)


@app.handle(image_registration_completed.ImageRegistrationCompleted)
def handle_image_registration_completed_event(
    event: image_registration_completed.ImageRegistrationCompleted,
):
    new_ami = ami.Ami(
        projectId=event.project_id,
        amiId=event.ami_id,
        amiName=event.ami_name,
        amiDescription=event.ami_description,
        createDate=event.create_date,
        lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        componentVersionDetails=[
            component_version_detail.ComponentVersionDetail(
                componentName=cmp.component_name,
                componentVersionType=cmp.component_version_type,
                softwareVendor=cmp.software_vendor,
                softwareVersion=cmp.software_version,
                licenseDashboard=cmp.license_dashboard,
                notes=cmp.notes,
            )
            for cmp in event.components_versions_details
        ],
        osVersion=event.os_version,
        platform=event.platform,
        architecture=event.architecture,
        integrations=event.integrations,
    )

    dependencies.update_ami_read_model_event_handler(new_ami, event.retired_ami_ids)


@app.handle(image_deregistered.ImageDeregistered)
def handle_image_deregistered_event(event: image_deregistered.ImageDeregistered):
    dependencies.delete_ami_read_model_event_handler(ami_id_value_object.from_str(event.ami_id))


@app.handle(image_imported.ImageImported)
def handle_image_imported_event(event: image_imported.ImageImported):
    component_details = []
    for cvd in event.componentVersionDetails or []:
        try:
            component_details.append(component_version_detail.ComponentVersionDetail(**cvd))
        except Exception as e:
            logger.warning(
                "Dropping malformed componentVersionDetail entry for image %s: %s (%s)", event.imageId, cvd, e
            )
    new_ami = ami.Ami(
        projectId=event.projectId,
        amiId=event.amiId,
        amiName=event.imageName,
        amiDescription=event.imageDescription,
        createDate=event.createDate,
        lastUpdateDate=datetime.now(timezone.utc).isoformat(),
        componentVersionDetails=component_details,
        osVersion=event.osVersion,
        platform=event.platform,
        architecture=event.architecture,
        integrations=[],
        imageSource=event.imageSource,
        marketplaceMetadata=event.marketplaceMetadata,
    )
    dependencies.update_ami_read_model_event_handler(new_ami, [])


@app.handle(automated_image_registration_completed.AutomatedImageRegistrationCompleted)
def handle_automated_image_registration_completed_event(
    event: automated_image_registration_completed.AutomatedImageRegistrationCompleted,
):
    try:
        component_details = [
            component_version_detail.ComponentVersionDetail(
                componentName=cmp.component_name,
                componentVersionType=cmp.component_version_type,
                softwareVendor=cmp.software_vendor,
                softwareVersion=cmp.software_version,
                licenseDashboard=cmp.license_dashboard,
                notes=cmp.notes,
            )
            for cmp in event.components_versions_details
        ]

        dependencies.create_automated_version_event_handler(
            ami_id=event.ami_id,
            product_id=event.product_id,
            project_id=event.project_id,
            release_type=event.release_type,
            user_id=event.user_id,
            component_version_details=component_details,
            os_version=event.os_version,
            platform=event.platform,
            architecture=event.architecture,
            integrations=event.integrations,
        )
    except Exception as e:
        logger.error(
            f"Failed to create automated product version for AMI {event.ami_id} and product {event.product_id}: {str(e)}"
        )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "PackagingEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: EventBridgeEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
