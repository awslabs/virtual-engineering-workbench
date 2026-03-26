from aws_lambda_powertools import logging
from pydantic import BaseModel

from app.shared.adapters.message_bus import (
    command_bus,
    command_bus_metrics,
    in_memory_command_bus,
)
from app.shared.instrumentation import power_tools_metrics
from app.usecase.domain.command_handlers import ping_command_handler
from app.usecase.domain.commands import ping_command
from app.usecase.entrypoints.api import config


class Dependencies(BaseModel):
    command_bus: command_bus.CommandBus

    class Config:
        arbitrary_types_allowed = True


def bootstrap(
    app_config: config.AppConfig,
    logger: logging.Logger,
) -> Dependencies:
    """Wire domain handlers to the command bus. Add your handlers here."""
    metrics_client = power_tools_metrics.PowerToolsMetrics()

    def _ping_handler_factory(_command: ping_command.PingCommand):
        return ping_command_handler.handle(cmd=_command)

    return Dependencies(
        command_bus=command_bus_metrics.CommandBusMetrics(
            inner=in_memory_command_bus.InMemoryCommandBus(logger=logger),
            metrics_client=metrics_client,
        ).register_handler(
            ping_command.PingCommand,
            _ping_handler_factory,
        )
    )
