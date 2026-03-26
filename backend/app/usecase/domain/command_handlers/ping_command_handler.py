from app.usecase.domain.commands import ping_command


def handle(cmd: ping_command.PingCommand) -> str:
    """Reference handler — replace with your domain logic."""
    return "pong"
