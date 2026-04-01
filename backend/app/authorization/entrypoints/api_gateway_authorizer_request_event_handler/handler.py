from aws_lambda_powertools import logging, metrics, tracing
from aws_lambda_powertools.utilities import typing
from aws_lambda_powertools.utilities.data_classes import (
    api_gateway_authorizer_event,
    event_source,
)
from aws_xray_sdk.core import patch_all

from app.authorization.domain.services.auth import authorizer
from app.authorization.entrypoints.api_gateway_authorizer_request_event_handler import (
    bootstrapper,
    config,
)
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

patch_all()

app_config = config.AppConfig()
default_region_name = app_config.get_default_region()

metrics_handler = metrics.Metrics()
logger = logging.Logger()
tracer = tracing.Tracer()

dependencies = bootstrapper.bootstrap(app_config, logger)


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metrics_handler.log_metrics(capture_cold_start_metric=True)
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.AsyncEventHandler: "APIGatewayAuthorizerRequestEvents"}
)
@event_source(data_class=api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent)
def handler(
    event: api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent,
    _: typing.LambdaContext,
):
    return dependencies.authorizer.authorize(
        authorizer.AuthorizationRequest(
            auth_token=event.get_header_value("Authorization"),
            api_id=event.request_context.api_id,
            operation_id=event.request_context.get("operationName"),
            resource_ids=event.path_parameters,
            resource=event.method_arn,
            resource_path=event.request_context.resource_path,
        )
    )
