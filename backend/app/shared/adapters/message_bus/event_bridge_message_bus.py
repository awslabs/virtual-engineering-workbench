import logging
from typing import Optional

from app.shared.adapters.message_bus import message_bus
from app.shared.api import aws_events_api, aws_scheduler_api


class EventBridgeMessageBus(message_bus.MessageBus):
    def __init__(
        self,
        events_api: aws_events_api.AWSEventsApi,
        event_bus_name: str,
        bounded_context_name: str,
        logger: logging.Logger,
        scheduler_api: Optional[aws_scheduler_api.AWSSchedulerApi] = None,
    ) -> None:
        super().__init__()

        self._events_api = events_api
        self._event_bus_name = event_bus_name
        self._bounded_context_name = bounded_context_name
        self._logger = logger
        self._scheduler_api = scheduler_api

    def publish(
        self,
        message: message_bus.Message,
        schedule_config: Optional[message_bus.ScheduleConfig] = None,
        flexible_config: Optional[message_bus.ScheduleFlexibleConfig] = None,
    ) -> None:

        event_json = self._construct_event_json(message)

        if schedule_config is None and flexible_config is None:
            self._logger.info(f"Publishing {message.event_name} event")
            self._logger.debug(message)
            self._events_api.put_event(
                source=self._bounded_context_name,
                detail=message.model_dump_json(by_alias=True),
                resources=[],
                detail_type=message.event_name,
                event_bus=self._event_bus_name,
            )
            return

        if self._scheduler_api is None:
            raise Exception("Scheduler API is not available")

        if schedule_config and flexible_config:
            raise Exception("Cannot provide both schedule_config and flexible_config simultaneously.")

        if flexible_config is not None:
            self._logger.info(f"Creating flexible schedule for {message.event_name} event")
            self._logger.debug(message)
            self._scheduler_api.create_flexible_schedule(flexible_config=flexible_config, event_json=event_json)
            return

        self._logger.info(f"Creating schedule for {message.event_name} event")
        self._logger.debug(message)
        self._scheduler_api.create_schedule(schedule_config=schedule_config, event_json=event_json)

    def reschedule(self, message: message_bus.Message, schedule_config: message_bus.ScheduleConfig) -> None:
        if self._scheduler_api is None:
            raise Exception("Scheduler API is not available")
        event_json = self._construct_event_json(message)
        self._scheduler_api.update_schedule(schedule_config=schedule_config, event_json=event_json)

    def unschedule(self, schedule_id: str) -> None:
        if self._scheduler_api is None:
            raise Exception("Scheduler API is not available")
        self._scheduler_api.delete_schedule(schedule_id=schedule_id)

    def _construct_event_json(self, message: message_bus.Message) -> dict:
        return {
            "Source": self._bounded_context_name,
            "Resources": [],
            "DetailType": message.event_name,
            "Detail": message.model_dump(by_alias=True),
        }
