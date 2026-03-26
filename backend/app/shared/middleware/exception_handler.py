import json
import os
import typing
from http.client import BAD_REQUEST, INTERNAL_SERVER_ERROR, NOT_FOUND, UNAUTHORIZED

from aws_lambda_powertools import logging
from aws_lambda_powertools.event_handler.exceptions import NotFoundError
from aws_lambda_powertools.middleware_factory import lambda_handler_decorator

from app.shared.middleware import authorization

logger = logging.Logger(level=os.environ.get("LOG_LEVEL", "INFO"), child=True)


@lambda_handler_decorator
def handle_exceptions(
    handler,
    event,
    context,
    user_exceptions,
    cors_config,
    user_exception_response_code=BAD_REQUEST,
    user_exception_details=True,
):
    """Decorator for handling exceptions and returning proper response to the client."""

    try:
        return handler(event, context)
    except NotFoundError as e:
        logger.exception("Not found exception.")
        return {
            "statusCode": NOT_FOUND,
            "headers": cors_config.to_dict(origin=get_header(event, "origin")),
            "body": json.dumps({"message": str(e)}),
            "isBase64Encoded": False,
        }
    except authorization.AuthException:
        logger.exception("Auth exception")
        return {
            "statusCode": UNAUTHORIZED,
            "headers": cors_config.to_dict(origin=get_header(event, "origin")),
            "body": json.dumps({"message": "Unauthorized"}),
            "isBase64Encoded": False,
        }
    except Exception as e:
        if isinstance(e, tuple(user_exceptions)):
            logger.exception("User exception.")
            return {
                "statusCode": user_exception_response_code,
                "headers": cors_config.to_dict(origin=get_header(event, "origin")),
                "body": json.dumps({"message": str(e) if user_exception_details else ""}),
                "isBase64Encoded": False,
            }
        else:
            logger.exception("Unhandled exception.")
            return {
                "statusCode": INTERNAL_SERVER_ERROR,
                "headers": cors_config.to_dict(origin=get_header(event, "origin")),
                "body": json.dumps({"message": "Internal server error."}),
                "isBase64Encoded": False,
            }


def get_header(event: dict, header: str) -> typing.Optional[str]:
    return event.get("headers", {}).get(header)


@lambda_handler_decorator
def handler_non_api_exceptions(handler, event, context):
    """Decorator for handling exceptions by `org-workbench-monitoring-cw_alarm_notifications`."""

    try:
        return handler(event, context)

    except Exception as e:
        logger.error(e, exc_info=True)
        raise e
