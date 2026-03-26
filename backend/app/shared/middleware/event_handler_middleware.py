import typing

from app.shared.adapters.boto import orchestration_service
from app.shared.middleware import event_handler

type CallbackTokenResolver = typing.Callable[[dict], str]


def saga_token_resolver(event: dict):
    return event.get("saga-command", {}).get("callback_token")


def use_orchestration(
    orchestration_svc: orchestration_service.OrchestrationService,
    callback_token_resolver: CallbackTokenResolver = saga_token_resolver,
) -> event_handler.MiddlewareHandlerFunc:

    def __use_orchestration(event: typing.Any, context: typing.Any, next: event_handler.HandlerFunc):
        try:
            return next(event, context)
        except Exception as e:
            if (callback_token := callback_token_resolver(event)) is not None:
                orchestration_svc.send_callback_failure(
                    callback_token=callback_token, error_type=type(e).__name__, error_message=str(e)
                )
            raise e

    return __use_orchestration
