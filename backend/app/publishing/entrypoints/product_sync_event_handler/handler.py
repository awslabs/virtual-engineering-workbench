from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import event_source
from aws_xray_sdk.core import patch_all

from app.publishing.domain.commands import products_versions_sync_command
from app.publishing.entrypoints.product_sync_event_handler import bootstrapper, config
from app.publishing.entrypoints.product_sync_event_handler.scheduled_job_events import (
    products_versions_sync_requested_job,
)
from app.shared.middleware import event_handler
from app.shared.middleware.custom_events import scheduled_job_event
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig()
default_region_name = app_config.get_default_region()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

app = event_handler.ScheduledJobEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger)


@app.handle(products_versions_sync_requested_job.ProductsVersionsSyncRequested)
def products_versions_sync_handler(event: products_versions_sync_requested_job.ProductsVersionsSyncRequested):
    command = products_versions_sync_command.ProductsVersionsSyncCommand()
    dependencies.command_bus.handle(command)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@event_source(data_class=scheduled_job_event.ScheduledJobEvent)
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "ScheduledJobs"})
def handler(
    event: scheduled_job_event.ScheduledJobEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
