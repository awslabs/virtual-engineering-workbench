import typing

from aws_lambda_powertools import logging

from app.shared.adapters.message_bus import command_bus


class InMemoryCommandBus(command_bus.CommandBus):
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._command_handlers: typing.Dict[str, typing.Callable] = {}

    def handle(self, command: command_bus.Command, handler_token: str | None = None) -> None:
        command_name = self._get_handler_name(type(command).__name__, handler_token)

        if command_name not in self._command_handlers:
            raise Exception(f"Command {command_name} does not have registered handlers")

        self._logger.info({"Command": command_name})

        self._logger.debug({"Payload": command.model_dump()})

        try:
            return self._command_handlers[command_name](command)
        except Exception as e:
            self._logger.error(e)
            raise e

    def register_handler(
        self,
        command_type: typing.Type,
        handler: typing.Callable[[command_bus.Command], None],
        handler_token: str | None = None,
    ) -> command_bus.CommandBus:
        handler_name = self._get_handler_name(command_type.__name__, handler_token)

        if handler_name in self._command_handlers:
            raise Exception(f"Command {handler_name} already has a handler.")

        self._logger.debug(f"Registered handler for {handler_name}")

        self._command_handlers[handler_name] = handler

        return self

    def _get_handler_name(self, command_name: str, handler_token: str | None) -> str:
        handler_name_parts = [part for part in [command_name, handler_token] if part]
        return "#".join(handler_name_parts)
