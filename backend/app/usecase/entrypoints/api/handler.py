from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.utilities import typing

from app.usecase.domain.commands import ping_command
from app.usecase.entrypoints.api import bootstrapper, config

app_config = config.AppConfig()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

app = APIGatewayRestResolver()
dependencies = bootstrapper.bootstrap(app_config, logger)


@app.get("/usecase/ping")
def ping():
    """Reference endpoint — replace with your API routes."""
    cmd = ping_command.PingCommand()
    result = dependencies.command_bus.handle(cmd)
    return {"message": result}


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
def handler(event: dict, context: typing.LambdaContext):
    return app.resolve(event, context)
