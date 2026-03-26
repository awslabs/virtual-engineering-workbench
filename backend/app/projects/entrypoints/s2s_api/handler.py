from aws_lambda_powertools import logging, tracing
from aws_lambda_powertools.event_handler import api_gateway
from aws_lambda_powertools.utilities import typing
from aws_xray_sdk.core import patch_all

from app.projects.domain.exceptions import domain_exception
from app.projects.entrypoints.s2s_api import bootstrapper, config
from app.projects.entrypoints.s2s_api.routers import assignments, enrolments, projects
from app.shared.logging.helpers import clear_auth_headers
from app.shared.middleware import authorization, exception_handler
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

logger = logging.Logger()
tracer = tracing.Tracer()

app_config = config.AppConfig(**config.config)
default_region_name = app_config.get_default_region()
secret_name = app_config.get_audit_logging_key_name()

dependencies = bootstrapper.bootstrap(app_config, logger)

cors_config = api_gateway.CORSConfig(**app_config.cors_config)
app = api_gateway.APIGatewayRestResolver(
    cors=cors_config,
    strip_prefixes=app_config.get_strip_prefixes(),
    enable_validation=True,
)
app.use(middlewares=[authorization.require_auth_context])
app.include_router(assignments.init(dependencies=dependencies))
app.include_router(projects.init(dependencies=dependencies))
app.include_router(enrolments.init(dependencies=dependencies))


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@exception_handler.handle_exceptions(user_exceptions=[domain_exception.DomainException], cors_config=cors_config)
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.ByAPI: "RestAPI"},
    enable_audit=True,
    region_name=default_region_name,
    secret_name=secret_name,
)
def handler(
    event: dict,
    context: typing.LambdaContext,
):
    logger.info(clear_auth_headers(event))
    return app.resolve(event, context)
