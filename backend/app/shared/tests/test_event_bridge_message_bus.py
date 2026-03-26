import logging
from datetime import datetime, timedelta
from unittest import mock

import assertpy
import pytest
from pydantic import Field

from app.shared.adapters.message_bus import event_bridge_message_bus, message_bus
from app.shared.api import aws_events_api, aws_scheduler_api

EVENT_BUS_NAME = "arn:aws:events:us-east-1:001234567890:event-bus/service-catalog-automation"
BOUNDED_CONTEXT_NAME = "org.virtual-workbench.web-app"


class FakeEvent(message_bus.Message):
    event_name: str = Field("FakeEvent", const=True, alias="eventName")
    some_param: str = Field(..., alias="someParam")

    class Config:
        allow_population_by_field_name = True


def test_message_bus_should_publish_event_to_event_bridge():
    # ARRANGE
    aws_events_api_mock = mock.create_autospec(spec=aws_events_api.AWSEventsApi, instance=True)
    logger_mock = mock.create_autospec(spec=logging.Logger)

    on_boarding_service = event_bridge_message_bus.EventBridgeMessageBus(
        events_api=aws_events_api_mock,
        event_bus_name=EVENT_BUS_NAME,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        logger=logger_mock,
    )

    evt = FakeEvent(some_param="Test")

    # ACT
    on_boarding_service.publish(evt)

    # ASSERT
    aws_events_api_mock.put_event.assert_called_once()
    publish_attributes = aws_events_api_mock.put_event.call_args.kwargs

    assertpy.assert_that(publish_attributes["source"]).is_equal_to(BOUNDED_CONTEXT_NAME)
    assertpy.assert_that(publish_attributes["detail"]).is_equal_to(evt.json(by_alias=True))
    assertpy.assert_that(publish_attributes["detail_type"]).is_equal_to("FakeEvent")
    assertpy.assert_that(publish_attributes["event_bus"]).is_equal_to(EVENT_BUS_NAME)


def test_message_bus_should_publish_event_to_event_bridge_with_schedule():
    # ARRANGE
    aws_events_api_mock = mock.create_autospec(spec=aws_events_api.AWSEventsApi, instance=True)
    logger_mock = mock.create_autospec(spec=logging.Logger)
    aws_scheduler_api_mock = mock.create_autospec(spec=aws_scheduler_api.AWSSchedulerApi, instance=True)

    on_boarding_service = event_bridge_message_bus.EventBridgeMessageBus(
        events_api=aws_events_api_mock,
        event_bus_name=EVENT_BUS_NAME,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        logger=logger_mock,
        scheduler_api=aws_scheduler_api_mock,
    )

    evt = FakeEvent(some_param="Test")
    schedule_config = message_bus.ScheduleConfig(EndTime=datetime.now() + timedelta(hours=1), ScheduleId="schedule-1")

    # ACT
    on_boarding_service.publish(evt, schedule_config)

    # ASSERT
    aws_scheduler_api_mock.create_schedule.assert_called_once()
    schedule_attributes = aws_scheduler_api_mock.create_schedule.call_args.kwargs
    assertpy.assert_that(schedule_attributes.get("event_json").get("Source")).is_equal_to(
        "org.virtual-workbench.web-app"
    )


def test_message_bus_update_scheduler_without_client_import_should_throw_exception():
    # ARRANGE
    aws_events_api_mock = mock.create_autospec(spec=aws_events_api.AWSEventsApi, instance=True)
    logger_mock = mock.create_autospec(spec=logging.Logger)

    on_boarding_service = event_bridge_message_bus.EventBridgeMessageBus(
        events_api=aws_events_api_mock,
        event_bus_name=EVENT_BUS_NAME,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        logger=logger_mock,
    )

    evt = FakeEvent(some_param="Test")
    schedule_config = message_bus.ScheduleConfig(EndTime=datetime.now() + timedelta(hours=1), ScheduleId="schedule-1")

    # ACT AND ASSERT
    with pytest.raises(Exception):
        on_boarding_service.publish(evt, schedule_config)


def test_message_bus_should_update_event_schedule():
    # ARRANGE
    aws_events_api_mock = mock.create_autospec(spec=aws_events_api.AWSEventsApi, instance=True)
    logger_mock = mock.create_autospec(spec=logging.Logger)
    aws_scheduler_api_mock = mock.create_autospec(spec=aws_scheduler_api.AWSSchedulerApi, instance=True)

    on_boarding_service = event_bridge_message_bus.EventBridgeMessageBus(
        events_api=aws_events_api_mock,
        event_bus_name=EVENT_BUS_NAME,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        logger=logger_mock,
        scheduler_api=aws_scheduler_api_mock,
    )

    evt = FakeEvent(some_param="Test")
    old_schedule_config = message_bus.ScheduleConfig(
        EndTime=datetime.now() + timedelta(hours=1), ScheduleId="schedule-1"
    )
    on_boarding_service.publish(evt, old_schedule_config)
    new_schedule_config = message_bus.ScheduleConfig(
        EndTime=datetime(2024, 8, 1, 16, 38, 30, 524799), ScheduleId="schedule-1"
    )

    # ACT
    on_boarding_service.reschedule(evt, new_schedule_config)

    # ASSERT
    aws_scheduler_api_mock.update_schedule.assert_called_once()
    schedule_attributes = aws_scheduler_api_mock.update_schedule.call_args.kwargs
    assertpy.assert_that(schedule_attributes.get("schedule_config")).is_equal_to(
        message_bus.ScheduleConfig(EndTime=datetime(2024, 8, 1, 16, 38, 30, 524799), ScheduleId="schedule-1")
    )
    assertpy.assert_that(schedule_attributes.get("event_json").get("Source")).is_equal_to(
        "org.virtual-workbench.web-app"
    )


def test_message_bus_delete_scheduler_without_client_import_should_throw_exception():
    # ARRANGE
    aws_events_api_mock = mock.create_autospec(spec=aws_events_api.AWSEventsApi, instance=True)
    logger_mock = mock.create_autospec(spec=logging.Logger)

    on_boarding_service = event_bridge_message_bus.EventBridgeMessageBus(
        events_api=aws_events_api_mock,
        event_bus_name=EVENT_BUS_NAME,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        logger=logger_mock,
    )

    # ACT AND ASSERT
    with pytest.raises(Exception):
        on_boarding_service.unschedule(schedule_id="schedule-1")


def test_message_bus_should_delete_event_schedule():
    # ARRANGE
    aws_events_api_mock = mock.create_autospec(spec=aws_events_api.AWSEventsApi, instance=True)
    logger_mock = mock.create_autospec(spec=logging.Logger)
    aws_scheduler_api_mock = mock.create_autospec(spec=aws_scheduler_api.AWSSchedulerApi, instance=True)

    on_boarding_service = event_bridge_message_bus.EventBridgeMessageBus(
        events_api=aws_events_api_mock,
        event_bus_name=EVENT_BUS_NAME,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        logger=logger_mock,
        scheduler_api=aws_scheduler_api_mock,
    )

    evt = FakeEvent(some_param="Test")
    schedule_config = message_bus.ScheduleConfig(EndTime=datetime.now() + timedelta(hours=1), ScheduleId="schedule-1")
    on_boarding_service.publish(evt, schedule_config)

    # ACT
    on_boarding_service.unschedule(schedule_id="schedule-1")

    # ASSERT
    aws_scheduler_api_mock.delete_schedule.assert_called_once()
