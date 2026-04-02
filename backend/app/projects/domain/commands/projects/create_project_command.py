from typing import Optional

from pydantic import ConfigDict

from app.shared.adapters.message_bus import command_bus


class CreateProjectCommand(command_bus.Command):
    name: str
    description: Optional[str] = None
    isActive: bool
    model_config = ConfigDict(arbitrary_types_allowed=True)
