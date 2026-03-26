from typing import Optional

from app.shared.adapters.message_bus import command_bus


class CreateProjectCommand(command_bus.Command):
    name: str
    description: Optional[str]
    isActive: bool

    class Config:
        arbitrary_types_allowed = True
