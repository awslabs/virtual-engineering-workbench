from http import HTTPStatus

from aws_lambda_powertools import logging, tracing
from aws_lambda_powertools.event_handler import api_gateway
from aws_lambda_powertools.event_handler.exceptions import NotFoundError
from aws_lambda_powertools.event_handler.middlewares.openapi_validation import RequestValidationError
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities import typing

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.exceptions.s2s_exception import S2SException
from app.packaging.entrypoints.s2s_api import bootstrapper, config, problem_details
from app.packaging.entrypoints.s2s_api.routers import common, component_versions, components, pipelines, recipes
from app.shared.logging.helpers import clear_auth_headers
from app.shared.middleware import authorization
from app.shared.middleware.metric import metric_handlers
from app.shared.middleware.metric.types import MetricDimensionNames

logger = logging.Logger()
tracer = tracing.Tracer()
app_config = config.AppConfig(**config.config)
cors_config = api_gateway.CORSConfig(**app_config.cors_config)
dependencies = bootstrapper.bootstrap(app_config, logger)

app = api_gateway.APIGatewayRestResolver(
    cors=cors_config,
    strip_prefixes=app_config.get_strip_prefixes(),
    enable_validation=True,
)
app.use(middlewares=[authorization.require_auth_context])
app.include_router(components.init(dependencies))
app.include_router(component_versions.init(dependencies))
app.include_router(recipes.init(dependencies))
app.include_router(pipelines.init(dependencies))


@app.exception_handler(RequestValidationError)
def handle_validation_error(error: RequestValidationError):
    logger.info("Packaging S2S request validation failed", errors=error.errors())
    return problem_details.api_response(
        HTTPStatus.BAD_REQUEST,
        detail="The request does not match the API contract.",
        code="INVALID_REQUEST",
        request_id=request_id(app.current_event.raw_event),
        retryable=False,
    )


@app.exception_handler(NotFoundError)
def handle_not_found(error: NotFoundError):
    return problem_details.api_response(
        HTTPStatus.NOT_FOUND,
        detail=str(error),
        code="NOT_FOUND",
        request_id=request_id(app.current_event.raw_event),
        retryable=False,
    )


def request_id(event: dict) -> str | None:
    return event.get("requestContext", {}).get("requestId")


def append_correlation_fields(event: dict) -> None:
    path_parameters = event.get("pathParameters") or {}
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    logger.append_keys(
        clientId=claims.get("client_id"),
        projectId=path_parameters.get("project_id") or path_parameters.get("projectId"),
        componentId=path_parameters.get("component_id") or path_parameters.get("componentId"),
        componentVersionId=path_parameters.get("version_id") or path_parameters.get("versionId"),
        requestId=request_id(event),
    )


def add_cors(response: dict, event: dict) -> dict:
    response["headers"].update(cors_config.to_dict(origin=(event.get("headers") or {}).get("origin")))
    return response


@tracer.capture_lambda_handler  # type: ignore
@logger.inject_lambda_context  # type: ignore
@metric_handlers.report_invocation_metrics(
    dimensions={MetricDimensionNames.ByAPI: "PackagingS2SAPI"},
    enable_audit=True,
    region_name=app_config.get_default_region(),
    secret_name=app_config.get_audit_logging_key_name(),
)
@common.api_metrics.log_metrics(raise_on_empty_metrics=False)
def handler(event: dict, context: typing.LambdaContext):
    common.api_metrics.add_metric(name="APIRequests", unit=MetricUnit.Count, value=1)
    append_correlation_fields(event)
    logger.info(clear_auth_headers(event))
    try:
        resolved = app.resolve(event, context)
        if "headers" not in resolved and "multiValueHeaders" in resolved:
            resolved["headers"] = {
                name: values[0] if isinstance(values, list) else values
                for name, values in resolved["multiValueHeaders"].items()
            }
        return resolved
    except S2SException as error:
        return add_cors(problem_details.s2s_response(error, request_id(event)), event)
    except domain_exception.DomainException as error:
        return add_cors(
            problem_details.response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=str(error),
                code="DOMAIN_VALIDATION_FAILED",
                request_id=request_id(event),
                retryable=False,
            ),
            event,
        )
    except authorization.AuthException:
        return add_cors(
            problem_details.response(
                HTTPStatus.UNAUTHORIZED,
                detail="Authentication is required.",
                code="UNAUTHORIZED",
                request_id=request_id(event),
                retryable=False,
            ),
            event,
        )
    except Exception:
        logger.exception("Unhandled Packaging S2S API error")
        return add_cors(
            problem_details.response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Internal server error.",
                code="INTERNAL_ERROR",
                request_id=request_id(event),
                retryable=True,
            ),
            event,
        )
