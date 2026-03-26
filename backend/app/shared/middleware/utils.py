import json
from functools import wraps
from typing import Any, Dict, Optional, Type

import pydantic
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.types import Model

from app.shared.middleware import authorization


def handle_response_type(response: Any) -> Dict[Any, Any]:
    if isinstance(response, pydantic.BaseModel):
        return response.dict()
    return response


def parse_event(model: Type[Model], app_context):
    """Decorator for parsing the lambda event into an object including the auth."""

    def real_decorator(function):
        @wraps(function)
        def wrapper(**kwargs):
            event = parse(event=app_context.current_event.json_body, model=model)
            principal = authorization.Principal(
                authType=authorization.AuthType.CognitoUserJWT,
                userName=app_context.current_event["requestContext"]["authorizer"]["userName"],
                userEmail=app_context.current_event["requestContext"]["authorizer"]["userEmail"],
                stages=set(json.loads(app_context.current_event["requestContext"]["authorizer"]["stages"])),
                userRoles=list(json.loads(app_context.current_event["requestContext"]["authorizer"]["userRoles"])),
                userDomains=list(json.loads(app_context.current_event["requestContext"]["authorizer"]["userDomains"])),
            )

            return handle_response_type(function(event, user_principal=principal, **kwargs))

        return wrapper

    return real_decorator


def parse_event_service_to_service_client(model: Optional[Type[Model]], app_context):
    """Decorator for parsing the lambda event into an object including auth information from calling service"""

    def real_decorator(function):
        @wraps(function)
        def wrapper(**kwargs):
            principal = authorization.Principal(
                authType=authorization.AuthType.CognitoServiceJWT,
                user_token=app_context.current_event["headers"]["Authorization"],
                userName=app_context.current_event["requestContext"]["authorizer"]["claims"]["client_id"],
            )

            if not model:
                return handle_response_type(function(user_principal=principal, **kwargs))

            event = parse(event=app_context.current_event.json_body, model=model)
            return handle_response_type(function(event, user_principal=principal, **kwargs))

        return wrapper

    return real_decorator


def parse_auth(app_context):
    """Decorator for parsing the auth object."""

    def real_decorator(function):
        @wraps(function)
        def wrapper(**kwargs):
            principal = authorization.Principal(
                authType=authorization.AuthType.CognitoUserJWT,
                userName=app_context.current_event["requestContext"]["authorizer"]["userName"],
                userEmail=app_context.current_event["requestContext"]["authorizer"]["userEmail"],
                stages=set(json.loads(app_context.current_event["requestContext"]["authorizer"]["stages"])),
                userRoles=list(json.loads(app_context.current_event["requestContext"]["authorizer"]["userRoles"])),
                userDomains=list(json.loads(app_context.current_event["requestContext"]["authorizer"]["userDomains"])),
            )

            return handle_response_type(function(user_principal=principal, **kwargs))

        return wrapper

    return real_decorator
