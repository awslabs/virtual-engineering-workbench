import unittest

import pytest

from app.shared.adapters.message_bus import command_bus, in_memory_command_bus


class FakeCommand(command_bus.Command):
    pass


def test_when_handler_is_registered_should_invoke_handler():
    # ARRANGE
    command = FakeCommand()

    mock_handler = unittest.mock.MagicMock()

    bus = in_memory_command_bus.InMemoryCommandBus(
        logger=unittest.mock.MagicMock(),
    ).register_handler(
        FakeCommand,
        mock_handler,
    )

    # ACT
    bus.handle(command)

    # ASSERT
    mock_handler.assert_called_once_with(command)


def test_when_handler_is_registered_with_config_token_should_invoke_handler():
    # ARRANGE
    command = FakeCommand()

    mock_handler = unittest.mock.MagicMock()
    mock_handler_v2 = unittest.mock.MagicMock()

    bus = (
        in_memory_command_bus.InMemoryCommandBus(
            logger=unittest.mock.MagicMock(),
        )
        .register_handler(
            FakeCommand,
            mock_handler,
            "v1",
        )
        .register_handler(
            FakeCommand,
            mock_handler_v2,
            "v2",
        )
    )

    # ACT
    bus.handle(command, "v2")

    # ASSERT
    mock_handler_v2.assert_called_once_with(command)
    mock_handler.assert_not_called()


def test_when_handler_is_registered_should_prevent_registering_again():
    # ARRANGE
    mock_handler = unittest.mock.MagicMock()

    bus = in_memory_command_bus.InMemoryCommandBus(
        logger=unittest.mock.MagicMock(),
    ).register_handler(
        FakeCommand,
        mock_handler,
    )

    # ACT
    with pytest.raises(Exception):
        bus.register_handler(
            FakeCommand,
            mock_handler,
        )
