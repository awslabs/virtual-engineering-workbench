import logging
from unittest import mock

import assertpy

from app.packaging.entrypoints.domain_event_handler import bootstrapper, config


def test_bootstrapper():
    # ARRANGE
    app_config = config.AppConfig()

    # ACT
    dependencies = bootstrapper.bootstrap(app_config=app_config, logger=logging.getLogger())

    # ASSERT
    assertpy.assert_that(dependencies).is_not_none()


def test_bootstrapper_wires_component_retirement_to_handler_signature(monkeypatch):
    handler = mock.create_autospec(bootstrapper.remove_component_version_command_handler.handle)
    monkeypatch.setattr(bootstrapper.remove_component_version_command_handler, "handle", handler)
    dependencies = bootstrapper.bootstrap(app_config=config.AppConfig(), logger=logging.getLogger())
    command = bootstrapper.remove_component_version_command.RemoveComponentVersionCommand.model_construct()

    dependencies.command_bus.handle(command)

    handler.assert_called_once()
    assert handler.call_args.kwargs["command"] is command
