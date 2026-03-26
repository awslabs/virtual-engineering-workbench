from app.usecase.domain.command_handlers import ping_command_handler
from app.usecase.domain.commands import ping_command


def test_ping_handler_returns_pong():
    # ARRANGE
    cmd = ping_command.PingCommand()

    # ACT
    result = ping_command_handler.handle(cmd)

    # ASSERT
    assert result == "pong"
