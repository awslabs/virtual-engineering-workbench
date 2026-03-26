import logging
import typing
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from aws_lambda_powertools.utilities.data_classes import EventBridgeEvent, api_gateway_authorizer_event
from pydantic import BaseModel

from app.shared.middleware.custom_events import scheduled_job_event, step_function_event


class EventBase(BaseModel, ABC): ...


class EventResolverException(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(msg)


type HandlerFunc = typing.Callable[[typing.Any, typing.Any], dict]
type MiddlewareHandlerFunc = typing.Callable[[typing.Any, typing.Any, HandlerFunc], dict]


class EventResolver(ABC):
    _handlers: Dict[str, Callable] = {}
    _event_constructors: Dict[str, Callable] = {}
    _middleware: list[MiddlewareHandlerFunc] = []

    context: dict[str, typing.Any] = {}

    def __init__(self, logger: logging.Logger, middleware: list[MiddlewareHandlerFunc] = []) -> None:
        super().__init__()
        self._logger = logger
        for m in middleware:
            self.use_middleware(m)

    def use_middleware(self, middleware: MiddlewareHandlerFunc):
        self._middleware.append(middleware)

    def handle(self, event_type: type, event_name: Optional[str] = None):
        def register_handler(func: Callable):
            evt_name = event_name if event_name else event_type.__name__

            self._logger.debug(f"Registering {func.__name__} as handler for {evt_name}")

            self._handlers[evt_name] = func
            self._event_constructors[evt_name] = event_type

            return func

        return register_handler

    def append_context(self, **kwargs):
        self.context.update(**kwargs)

    def resolve(self, event: Any, context: Any):

        def __resolve(event: Any, context: Any):
            self._logger.debug(event)

            event_name, event_raw_payload = self.parse_event(event, context)

            if event_name not in self._handlers or event_name not in self._event_constructors:
                raise EventResolverException(f"Event handler for {event_name} is not registered.")

            self._logger.info(f"Handling {event_name} with {self._handlers[event_name].__name__}")
            self._logger.debug(f"Raw Event: {event_raw_payload}")
            self._logger.debug(f"Event Constructor: {self._event_constructors[event_name]}")

            # If the event is already an instance of the expected type, use it directly
            if isinstance(event_raw_payload, self._event_constructors[event_name]):
                evt = event_raw_payload
            else:
                # Only try parse_obj if the constructor is a Pydantic model
                if hasattr(self._event_constructors[event_name], "parse_obj"):
                    evt = self._event_constructors[event_name].parse_obj(event_raw_payload)
                else:
                    # Fallback to constructor if not a Pydantic model
                    evt = self._event_constructors[event_name](event_raw_payload)

            self.context.clear()

            try:
                return self._handlers[event_name](evt)
            finally:
                self.context.clear()

        event_handlers: list[HandlerFunc] = [__resolve]

        def __append_middleware(m: MiddlewareHandlerFunc):
            handler = event_handlers[-1]
            return lambda event, context: m(event, context, handler)

        for m in reversed(self._middleware):
            event_handlers.append(__append_middleware(m))

        return event_handlers[-1](event, context)

    @abstractmethod
    def parse_event(self, event: Any, context: Any) -> tuple[str, dict]: ...


class EventBridgeEventResolver(EventResolver):
    def __init__(self, logger: logging.Logger, middleware: list[MiddlewareHandlerFunc] = []) -> None:
        super().__init__(logger, middleware)

    def parse_event(self, event: Any, context: Any):
        if not isinstance(event, EventBridgeEvent):
            raise EventResolverException("EventBridgeEventResolver can only handle events of type EventBridgeEvent")

        return event.detail_type, event.detail


class APIGatewayAuthorizerRequestEventResolver(EventResolver):
    def __init__(self, logger: logging.Logger, middleware: list[MiddlewareHandlerFunc] = []) -> None:
        super().__init__(logger, middleware)

    def parse_event(self, event: Any, context: Any):
        if not isinstance(event, api_gateway_authorizer_event.APIGatewayAuthorizerRequestEvent):
            raise EventResolverException(
                "APIGatewayAuthorizerRequestEventResolver can only handle events of type APIGatewayAuthorizerRequestEvent"
            )

        return event.get_type, event.headers


class StepFunctionEventResolver(EventResolver):
    def __init__(self, logger: logging.Logger, middleware: list[MiddlewareHandlerFunc] = []) -> None:
        super().__init__(logger, middleware)

    def parse_event(self, event: Any, context: Any):
        if not isinstance(event, step_function_event.StepFunctionEvent):
            raise EventResolverException("StepFunctionEventResolver can only handle events of type StepFunctionEvent")

        return event.event_type, event.raw_event


class SagaEventResolver(EventResolver):
    def __init__(self, logger: logging.Logger, middleware: list[MiddlewareHandlerFunc] = []) -> None:
        super().__init__(logger, middleware)

    def parse_event(self, event: Any, context: Any):
        if not (evt_details := self.__parse_event(event)):
            raise EventResolverException(
                "SagaEventResolver can handle either EventBridge events or StepFunction commands."
            )

        return evt_details

    def __parse_event(self, event: Any) -> tuple[str, dict]:
        if "detail-type" in event and "detail" in event:
            return (event.get("detail-type"), event.get("detail"))

        if "saga-command-name" in event and "saga-command" in event:
            return (event.get("saga-command-name"), event.get("saga-command"))

        return None


class ScheduledJobEventResolver(EventResolver):
    def __init__(self, logger: logging.Logger, middleware: list[MiddlewareHandlerFunc] = []) -> None:
        super().__init__(logger, middleware)

    def parse_event(self, event: Any, context: Any):
        if not isinstance(event, scheduled_job_event.ScheduledJobEvent):
            raise EventResolverException("ScheduledJobEventResolver can only handle events of type ScheduledJobEvent")

        return event.job_name, event.parameters or {}
