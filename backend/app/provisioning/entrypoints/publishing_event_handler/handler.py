from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source

from app.provisioning.domain.commands.product_provisioning import (
    check_if_upgrade_available_command,
)
from app.provisioning.domain.read_models import product
from app.provisioning.domain.value_objects import (
    product_id_value_object,
    product_version_id_value_object,
    product_version_name_value_object,
    region_value_object,
    version_stage_value_object,
)
from app.provisioning.entrypoints.publishing_event_handler import bootstrapper, config
from app.provisioning.entrypoints.publishing_event_handler.integration_events import (
    product_availability_updated,
    product_version_published,
    recommended_version_set,
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


@app.handle(product_availability_updated.ProductAvailabilityUpdated)
def handle_product_availability_updated(
    event: product_availability_updated.ProductAvailabilityUpdated,
):
    # Prepare event
    product_obj = product.Product(
        projectId=event.project_id,
        productId=event.product_id,
        technologyId=event.technology_id,
        technologyName=event.technology_name,
        productName=event.product_name,
        productType=event.product_type,
        productDescription=event.product_description,
        availableStages=event.available_stages,
        availableRegions=event.available_regions,
        pausedStages=event.paused_stages,
        pausedRegions=event.paused_regions,
        lastUpdateDate=event.last_update_date,
    )
    # Execute event handler
    dependencies.update_product_read_model_event_handler(product_obj)


@app.handle(recommended_version_set.RecommendedVersionSet)
def handle_recommended_version_set(
    event: recommended_version_set.RecommendedVersionSet,
):
    # Execute event handler
    dependencies.update_recommended_version_read_model_event_handler(
        project_id=event.project_id,
        product_id=event.product_id,
        new_recommended_version_id=event.version_id,
    )


@app.handle(product_version_published.ProductVersionPublished)
def handle_version_published(event: product_version_published.ProductVersionPublished):
    dependencies.command_bus.handle(
        check_if_upgrade_available_command.CheckIfUpgradeAvailableCommand(
            product_id=product_id_value_object.from_str(event.product_id),
            product_version_id=product_version_id_value_object.from_str(event.version_id),
            product_version_name=product_version_name_value_object.from_str(event.version_name),
            region=region_value_object.from_str(event.region),
            stage=version_stage_value_object.from_str(event.stage),
        )
    )


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "PublishingEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: EventBridgeEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
