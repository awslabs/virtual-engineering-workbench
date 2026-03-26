from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, event_source

from app.publishing.domain.commands import create_portfolio_command
from app.publishing.domain.value_objects import (
    account_id_value_object,
    aws_account_id_value_object,
    project_id_value_object,
    region_value_object,
    stage_value_object,
    tech_id_value_object,
)
from app.publishing.entrypoints.projects_event_handler import bootstrapper, config
from app.publishing.entrypoints.projects_event_handler.integration_events import (
    project_account_on_boarded,
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

logger.debug("Dummy change to trigger env variable deployment.")


@app.handle(project_account_on_boarded.ProjectAccountOnBoarded)
def handle_project_account_on_boarded(
    event: project_account_on_boarded.ProjectAccountOnBoarded,
):
    # Prepare create portfolio command
    create_portfolio_cmd = create_portfolio_command.CreatePortfolioCommand(
        projectId=project_id_value_object.from_str(event.project_id),
        technologyId=tech_id_value_object.from_str(event.technology_id),
        awsAccountId=aws_account_id_value_object.from_str(event.aws_account_id),
        accountId=account_id_value_object.from_str(event.account_id),
        stage=stage_value_object.from_str(event.stage),
        region=region_value_object.from_str(event.region),
    )

    # Execute command handler
    dependencies.command_bus.handle(create_portfolio_cmd)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(
    capture_cold_start_metric=True
)  # ensures metrics are flushed upon request completion/failure
@metric_handlers.report_invocation_metrics(dimensions={MetricDimensionNames.AsyncEventHandler: "ProjectsEvents"})
@event_source(data_class=EventBridgeEvent)
def handler(
    event: EventBridgeEvent,
    context: typing.LambdaContext,
):
    return app.resolve(event, context)
