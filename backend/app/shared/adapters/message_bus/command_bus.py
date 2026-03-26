from __future__ import annotations

import typing
from abc import ABC, abstractmethod

from pydantic import BaseModel, root_validator


class Command(BaseModel, ABC): ...


class SagaCommand(Command):

    @root_validator(pre=True)
    def construct_value_objects(cls, values):
        for field_name, field_info in cls.__fields__.items():
            alias = field_info.alias or field_name
            if alias in values and hasattr(field_info.type_, "from_obj"):
                if isinstance(values[alias], list):
                    values[alias] = [field_info.type_.from_obj(val) for val in values[alias]]
                else:
                    values[alias] = field_info.type_.from_obj(values[alias])
        return values


class CommandBus(ABC):
    @abstractmethod
    def handle(self, command: Command, handler_token: str | None = None) -> None: ...

    @abstractmethod
    def register_handler(
        self, command_type: typing.Type, handler: typing.Callable[[Command], None], handler_token: str | None = None
    ) -> CommandBus: ...
