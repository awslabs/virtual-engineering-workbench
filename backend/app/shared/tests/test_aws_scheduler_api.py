from datetime import datetime, timedelta

import assertpy
import boto3
import moto
import pytest

from app.shared.adapters.message_bus import message_bus
from app.shared.api import aws_scheduler_api

ROLE_ARN = "test-arn"
EVENT_BUS_ARN = "arn:aws:events:us-west-2:123456789012:event-bus/default"
BOUNDED_CONTEXT_NAME = "proserve.workbench.test_bc.dev"


@pytest.fixture(autouse=True)
def mock_scheduler_client():
    with moto.mock_aws():
        yield boto3.client("scheduler", "us-east-1")


def test_create_schedule(mock_scheduler_client):
    # ARRANGE
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=mock_scheduler_client,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        role_arn=ROLE_ARN,
        event_bus_arn=EVENT_BUS_ARN,
    )
    mock_scheduler_client.create_schedule_group(Name=scheduler_api._bounded_context_name)
    end_time = datetime.now() + timedelta(hours=1)
    schedule_config = message_bus.ScheduleConfig(EndTime=end_time, ScheduleId="schedule-1")
    event_json = {
        "Source": "my_bounded_context",
        "Resources": [],
        "DetailType": "user_created",
        "Detail": {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
    }

    # ACT
    response = scheduler_api.create_schedule(schedule_config, event_json)

    # ASSERT
    assertpy.assert_that(response.schedule_arn).is_not_none()
    assertpy.assert_that(response.schedule_arn).starts_with("arn:aws:scheduler:")


def test_create_flexible_schedule(mock_scheduler_client):
    # ARRANGE
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=mock_scheduler_client,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        role_arn=ROLE_ARN,
        event_bus_arn=EVENT_BUS_ARN,
    )
    mock_scheduler_client.create_schedule_group(Name=scheduler_api._bounded_context_name)
    end_time = datetime.now() + timedelta(hours=1)
    schedule_config = message_bus.ScheduleFlexibleConfig(
        EndTime=end_time,
        ScheduleId="schedule-1",
        FlexibleTimeWindow=True,
        CronExpression="cron(0 23 ? * 7 *)",
    )
    event_json = {
        "Source": "my_bounded_context",
        "Resources": [],
        "DetailType": "user_created",
        "Detail": {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
    }

    # ACT
    response = scheduler_api.create_flexible_schedule(schedule_config, event_json)

    # ASSERT
    assertpy.assert_that(response.schedule_arn).is_not_none()
    assertpy.assert_that(response.schedule_arn).starts_with("arn:aws:scheduler:")


def test_update_schedule(mock_scheduler_client):
    # ARRANGE
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=mock_scheduler_client,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        role_arn=ROLE_ARN,
        event_bus_arn=EVENT_BUS_ARN,
    )
    mock_scheduler_client.create_schedule_group(Name=scheduler_api._bounded_context_name)
    event_json = {
        "Source": "my_bounded_context",
        "Resources": [],
        "DetailType": "user_created",
        "Detail": {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
    }
    old_end_time = datetime.now() + timedelta(hours=3)
    old_schedule_config = message_bus.ScheduleConfig(EndTime=old_end_time, ScheduleId="schedule-1")
    old_schedule_arn = scheduler_api.create_schedule(old_schedule_config, event_json)
    new_end_time = datetime.now() + timedelta(hours=3)
    new_schedule_config = message_bus.ScheduleConfig(EndTime=new_end_time, ScheduleId="schedule-1")

    # ACT
    response = scheduler_api.update_schedule(new_schedule_config, event_json)

    # ASSERT
    assertpy.assert_that(response.schedule_arn).is_not_none()
    assertpy.assert_that(response.schedule_arn).starts_with("arn:aws:scheduler:")
    assertpy.assert_that(response.schedule_arn).is_not_equal_to(old_schedule_arn)


def test_update_non_existing_schedule_should_throw_exception(mock_scheduler_client):
    # ARRANGE
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=mock_scheduler_client,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        role_arn=ROLE_ARN,
        event_bus_arn=EVENT_BUS_ARN,
    )
    event_json = {
        "Source": "my_bounded_context",
        "Resources": [],
        "DetailType": "user_created",
        "Detail": {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
    }
    new_end_time = datetime.now() + timedelta(hours=3)
    new_schedule_config = message_bus.ScheduleConfig(EndTime=new_end_time, ScheduleId="schedule-1")

    # ACT AND ASSERT
    with pytest.raises(Exception):
        scheduler_api.update_schedule(new_schedule_config, event_json)


def test_delete_schedule(mock_scheduler_client):
    # ARRANGE
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=mock_scheduler_client,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        role_arn=ROLE_ARN,
        event_bus_arn=EVENT_BUS_ARN,
    )
    mock_scheduler_client.create_schedule_group(Name=scheduler_api._bounded_context_name)
    event_json = {
        "Source": "my_bounded_context",
        "Resources": [],
        "DetailType": "user_created",
        "Detail": {"id": 1, "name": "John Doe", "email": "john.doe@example.com"},
    }
    end_time = datetime.now() + timedelta(hours=3)
    schedule_config = message_bus.ScheduleConfig(EndTime=end_time, ScheduleId="schedule-1")
    create_schedule_resp = scheduler_api.create_schedule(schedule_config, event_json)

    # ACT
    all_schedules_before = mock_scheduler_client.list_schedules()
    response = scheduler_api.delete_schedule(schedule_id=schedule_config.schedule_id)
    all_schedules_after = mock_scheduler_client.list_schedules()

    # ASSERT
    assertpy.assert_that(response).is_none()
    assertpy.assert_that(all_schedules_before.get("Schedules")[0].get("Arn")).is_equal_to(
        create_schedule_resp.schedule_arn
    )
    assertpy.assert_that(all_schedules_after.get("Schedules")).is_empty()


def test_delete_non_existing_schedule_should_throw_exception(mock_scheduler_client):
    # ARRANGE
    scheduler_api = aws_scheduler_api.AWSSchedulerApi(
        client=mock_scheduler_client,
        bounded_context_name=BOUNDED_CONTEXT_NAME,
        role_arn=ROLE_ARN,
        event_bus_arn=EVENT_BUS_ARN,
    )
    mock_scheduler_client.create_schedule_group(Name=scheduler_api._bounded_context_name)
    end_time = datetime.now() + timedelta(hours=1)
    schedule_config = message_bus.ScheduleConfig(EndTime=end_time, ScheduleId="schedule-1")

    # ACT AND ASSERT
    with pytest.raises(Exception):
        scheduler_api.delete_schedule(schedule_id=schedule_config.schedule_id)
