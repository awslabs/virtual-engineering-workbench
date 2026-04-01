import json
import logging
from datetime import datetime
from typing import Optional
from unittest import mock

import pydantic

from app.shared.adapters.message_bus import message_bus, message_bus_metrics
from app.shared.instrumentation import metrics


class Event(message_bus.Message):
    event_name: str = pydantic.Field("Event", alias="eventName", json_schema_extra={"name": "Event Name"})


class ScheduleConfig(message_bus_metrics.ScheduleConfig):
    end_time: datetime = pydantic.Field(datetime.now(), alias="endTime", json_schema_extra={"name": "End Time"})
    schedule_id: str = pydantic.Field("Schedule ID", alias="scheduleId", json_schema_extra={"name": "Schedule ID"})


class ScheduleFlexibleConfig(message_bus.ScheduleFlexibleConfig):
    end_time: datetime = pydantic.Field("2025-02-13 04:00:00", alias="EndTime")
    schedule_id: str = pydantic.Field("AutoUpgrade-b8dff9ec-e630-4f65-9f10-b760eb4cc1a5", alias="ScheduleId")
    flexible_time_window: bool = pydantic.Field(True, alias="FlexibleTimeWindow")
    cron_expression: Optional[str] = pydantic.Field("cron(0 22 ? * 4 *)", alias="CronExpression")


def test_message_bus_metrics_should_publish_event_and_a_metric():
    # ARRANGE
    mb = mock.create_autospec(spec=message_bus.MessageBus)
    mc = mock.create_autospec(spec=metrics.Metrics)
    lg = mock.create_autospec(spec=logging.Logger)

    evt = Event()

    client = message_bus_metrics.MessageBusMetrics(inner=mb, metrics_client=mc, logger=lg)

    # ACT
    client.publish(evt)

    # ASSERT
    mb.publish.assert_called_with(evt, schedule_config=None, flexible_config=None)
    mc.publish_counter.assert_called_with(metric_name="Event", metric_type=metrics.MetricType.DomainEvent)


def test_message_bus_metrics_should_create_scheduler_and_a_metric():
    # ARRANGE
    mb = mock.create_autospec(spec=message_bus.MessageBus)
    mc = mock.create_autospec(spec=metrics.Metrics)
    lg = mock.create_autospec(spec=logging.Logger)

    evt = Event()
    schedule_config = ScheduleConfig()

    client = message_bus_metrics.MessageBusMetrics(inner=mb, metrics_client=mc, logger=lg)

    # ACT
    client.publish(evt, schedule_config)

    # ASSERT
    mb.publish.assert_called_with(evt, schedule_config=schedule_config, flexible_config=None)
    mc.publish_counter.assert_called_with(metric_name="Event.schedule", metric_type=metrics.MetricType.DomainEvent)


def test_message_bus_metrics_should_create_flexible_scheduler_and_a_metric():
    # ARRANGE
    mb = mock.create_autospec(spec=message_bus.MessageBus)
    mc = mock.create_autospec(spec=metrics.Metrics)
    lg = mock.create_autospec(spec=logging.Logger)

    evt = Event()
    flexible_config = ScheduleFlexibleConfig()

    client = message_bus_metrics.MessageBusMetrics(inner=mb, metrics_client=mc, logger=lg)

    # ACT
    client.publish(evt, flexible_config=flexible_config)

    # ASSERT
    mb.publish.assert_called_with(evt, schedule_config=None, flexible_config=flexible_config)
    mc.publish_counter.assert_called_with(metric_name="Event.schedule", metric_type=metrics.MetricType.DomainEvent)


def test_message_bus_metrics_should_update_scheduler_and_a_metric():
    # ARRANGE
    mb = mock.create_autospec(spec=message_bus.MessageBus)
    mc = mock.create_autospec(spec=metrics.Metrics)
    lg = mock.create_autospec(spec=logging.Logger)

    evt = Event()
    schedule_config = ScheduleConfig()

    client = message_bus_metrics.MessageBusMetrics(inner=mb, metrics_client=mc, logger=lg)

    # ACT
    client.reschedule(evt, schedule_config=schedule_config)

    # ASSERT
    mb.reschedule.assert_called_with(evt, schedule_config)
    mc.publish_counter.assert_called_with(metric_name="Event.reschedule", metric_type=metrics.MetricType.DomainEvent)


def test_message_bus_metrics_should_delete_scheduler_and_a_metric():
    # ARRANGE
    mb = mock.create_autospec(spec=message_bus.MessageBus)
    mc = mock.create_autospec(spec=metrics.Metrics)
    lg = mock.create_autospec(spec=logging.Logger)

    schedule_config = ScheduleConfig()

    client = message_bus_metrics.MessageBusMetrics(inner=mb, metrics_client=mc, logger=lg)

    # ACT
    client.unschedule(schedule_config.schedule_id)

    # ASSERT
    mb.unschedule.assert_called_with(schedule_config.schedule_id)
    mc.publish_counter.assert_called_with(
        metric_name="DeleteEventScheduler", metric_type=metrics.MetricType.DomainEvent
    )


def test_message_with_event_context():
    # ARRANGE
    evt = Event()
    # ACT
    event_time = evt.event_context.event_time
    # ASSERT
    assert event_time is not None


def test_message_with_event_context_should_serialize():
    # ARRANGE
    evt = Event()
    # ACT
    event_json = evt.model_dump_json()
    event_dict = json.loads(event_json)
    # ASSERT
    assert "event_context" in event_dict
    assert "event_time" in event_dict["event_context"]
    assert event_dict["event_context"]["event_time"] is not None
