import json
from http import HTTPStatus

from aws_lambda_powertools.event_handler import api_gateway

from app.packaging.domain.exceptions.s2s_exception import (
    InsufficientScope,
    ProjectAccessDenied,
    ProjectAccessUnavailable,
    S2SException,
)
from app.packaging.entrypoints.s2s_api.model.api_model import ProblemDetails

PROBLEM_CONTENT_TYPE = "application/problem+json"


def status_for(error: S2SException) -> HTTPStatus:
    if isinstance(error, (ProjectAccessDenied, InsufficientScope)):
        return HTTPStatus.FORBIDDEN
    if isinstance(error, ProjectAccessUnavailable):
        return HTTPStatus.SERVICE_UNAVAILABLE
    return HTTPStatus.INTERNAL_SERVER_ERROR


def response(
    status: HTTPStatus,
    *,
    detail: str,
    code: str,
    request_id: str | None,
    retryable: bool,
) -> dict:
    body = ProblemDetails(
        type=f"https://problems.virtual-engineering-workbench.dev/{code.lower().replace('_', '-')}",
        title=status.phrase,
        status=int(status),
        detail=detail,
        code=code,
        requestId=request_id,
        retryable=retryable,
    )
    return {
        "statusCode": int(status),
        "headers": {"Content-Type": PROBLEM_CONTENT_TYPE, "Cache-Control": "no-store"},
        "body": json.dumps(body.model_dump(mode="json", exclude_none=True)),
        "isBase64Encoded": False,
    }


def s2s_response(error: S2SException, request_id: str | None) -> dict:
    return response(
        status_for(error),
        detail=error.detail,
        code=error.code,
        request_id=request_id,
        retryable=error.retryable,
    )


def api_response(
    status: HTTPStatus,
    *,
    detail: str,
    code: str,
    request_id: str | None,
    retryable: bool,
) -> api_gateway.Response:
    response_dict = response(
        status,
        detail=detail,
        code=code,
        request_id=request_id,
        retryable=retryable,
    )
    return api_gateway.Response(
        status_code=response_dict["statusCode"],
        body=response_dict["body"],
        headers={"Cache-Control": "no-store"},
        content_type=PROBLEM_CONTENT_TYPE,
    )
