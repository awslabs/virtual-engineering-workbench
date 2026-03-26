from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source
from aws_xray_sdk.core import patch_all

from app.authorization.domain.integration_events.projects import (
    enrolment_approved,
    user_assigned,
    user_reassigned,
    user_unassigned,
)
from app.authorization.entrypoints.projects_event_handler import bootstrapper, config
from app.shared.middleware import event_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig()
default_region_name = app_config.get_default_region()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

app = event_handler.EventBridgeEventResolver(logger=logger)
dependencies = bootstrapper.bootstrap(app_config, logger)


@app.handle(enrolment_approved.EnrolmentApproved)
def enrolment_approved_ep(event: enrolment_approved.EnrolmentApproved):
    dependencies.enrolment_approved_handler(event)


@app.handle(user_assigned.UserAssigned)
def user_assigned_ep(event: user_assigned.UserAssigned):
    dependencies.user_assigned_handler(event)


@app.handle(user_reassigned.UserReAssigned)
def user_reassigned_ep(event: user_reassigned.UserReAssigned):
    dependencies.user_reassigned_handler(event)


@app.handle(user_unassigned.UserUnAssigned)
def user_unassigned_ep(event: user_unassigned.UserUnAssigned):
    dependencies.user_unassigned_handler(event)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "ProjectsEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
