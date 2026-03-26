import typing

from app.shared.adapters.message_bus import command_bus
from app.shared.instrumentation import metrics


class CommandBusMetrics(command_bus.CommandBus):
    def __init__(self, inner: command_bus.CommandBus, metrics_client: metrics.Metrics) -> None:
        self._inner = inner
        self._metrics_client = metrics_client

    def handle(self, command: command_bus.Command, handler_token: str | None = None) -> None:
        command_name = self._get_handler_name(type(command).__name__, handler_token)

        try:
            ret_val = self._inner.handle(command=command, handler_token=handler_token)
            self._metrics_client.publish_counter(
                metric_name=command_name, metric_type=metrics.MetricType.SuccessfullCommand
            )
            return ret_val
        except Exception as e:
            self._metrics_client.publish_counter(metric_name=command_name, metric_type=metrics.MetricType.FailedCommand)
            raise e

    def register_handler(
        self,
        command_type: typing.Type,
        handler: typing.Callable[[command_bus.Command], None],
        handler_token: str | None = None,
    ) -> command_bus.CommandBus:
        self._inner.register_handler(command_type=command_type, handler=handler, handler_token=handler_token)
        return self

    def _get_handler_name(self, command_name: str, handler_token: str | None) -> str:
        handler_name_parts = [part for part in [command_name, handler_token] if part]
        return ".".join(handler_name_parts)
