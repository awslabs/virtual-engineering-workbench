from unittest import mock

import assertpy
import pytest

from app.shared.adapters.message_bus import command_bus, command_bus_metrics
from app.shared.instrumentation import metrics


class FakeCommand(command_bus.Command):
    pass


def test_command_bus_metrics_command_succeeds_should_publish_success_metric():
    # ARRANGE
    command = FakeCommand()

    mock_inner = mock.create_autospec(spec=command_bus.CommandBus)
    mc = mock.create_autospec(spec=metrics.Metrics)

    bus = command_bus_metrics.CommandBusMetrics(
        inner=mock_inner,
        metrics_client=mc,
    )

    # ACT
    bus.handle(command)

    # ASSERT
    mock_inner.handle.assert_called_once_with(command=command, handler_token=None)
    mc.publish_counter.assert_called_with(metric_name="FakeCommand", metric_type=metrics.MetricType.SuccessfullCommand)


def test_command_bus_metrics_command_fails_should_publish_failure_metric():
    # ARRANGE
    command = FakeCommand()

    mock_inner = mock.create_autospec(spec=command_bus.CommandBus)
    mock_inner.handle.side_effect = Exception("Test")
    mc = mock.create_autospec(spec=metrics.Metrics)

    bus = command_bus_metrics.CommandBusMetrics(
        inner=mock_inner,
        metrics_client=mc,
    )

    # ACT
    with pytest.raises(Exception):
        bus.handle(command)

    # ASSERT
    mock_inner.handle.assert_called_once_with(command=command, handler_token=None)
    mc.publish_counter.assert_called_with(metric_name="FakeCommand", metric_type=metrics.MetricType.FailedCommand)


def test_command_bus_metrics_register_handler_calls_inner():
    # ARRANGE
    mock_handler = mock.MagicMock()
    mock_inner = mock.create_autospec(spec=command_bus.CommandBus)
    mc = mock.create_autospec(spec=metrics.Metrics)

    bus = command_bus_metrics.CommandBusMetrics(
        inner=mock_inner,
        metrics_client=mc,
    )

    # ACT
    bus_resp = bus.register_handler(
        FakeCommand,
        mock_handler,
    )

    # ASSERT
    mock_inner.register_handler.assert_called_once_with(
        command_type=FakeCommand, handler=mock_handler, handler_token=None
    )
    assertpy.assert_that(bus_resp).is_equal_to(bus)
