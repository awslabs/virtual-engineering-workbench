import logging
from typing import Optional

from app.shared.adapters.message_bus import message_bus
from app.shared.api import aws_events_api, aws_scheduler_api


class FailedEntriesException(Exception):
    """PutEvents returned HTTP 200 but rejected the entry (``FailedEntryCount > 0``)."""


class EventBridgeMessageBus(message_bus.MessageBus):
    """Publishes domain events to EventBridge, or schedules them.

    PutEvents reports per-entry failures (throttling, internal failure) in
    a successful HTTP 200 response. With ``raise_on_failed_entries=False``
    (the default) such a failure is not detected and the event is lost
    silently. With ``True``, :meth:`publish` raises
    :class:`FailedEntriesException` carrying each entry's ``ErrorCode`` and
    ``ErrorMessage``. Turn it on only where the caller handles a raised
    publish, because callers that commit state and then publish (for
    example ``AggregatePublisher``) would fail after the commit.
    """

    def __init__(
        self,
        events_api: aws_events_api.AWSEventsApi,
        event_bus_name: str,
        bounded_context_name: str,
        logger: logging.Logger,
        scheduler_api: Optional[aws_scheduler_api.AWSSchedulerApi] = None,
        raise_on_failed_entries: bool = False,
    ) -> None:
        super().__init__()

        self._events_api = events_api
        self._event_bus_name = event_bus_name
        self._bounded_context_name = bounded_context_name
        self._logger = logger
        self._scheduler_api = scheduler_api
        self._raise_on_failed_entries = raise_on_failed_entries

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
            response = self._events_api.put_event(
                source=self._bounded_context_name,
                detail=message.model_dump_json(by_alias=True),
                resources=[],
                detail_type=message.event_name,
                event_bus=self._event_bus_name,
            )
            if self._raise_on_failed_entries:
                self._raise_for_failed_entries(message, response)
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

    @staticmethod
    def _raise_for_failed_entries(message: message_bus.Message, response: aws_events_api.PutEventsResponse) -> None:
        if response.failed_entry_count <= 0:
            return
        errors = "; ".join(
            f"{entry.get('ErrorCode')}: {entry.get('ErrorMessage')}"
            for entry in response.entries
            if isinstance(entry, dict) and entry.get("ErrorCode")
        )
        raise FailedEntriesException(
            f"EventBridge rejected {response.failed_entry_count} entry(ies) for {message.event_name}: "
            f"{errors or 'no error detail returned'}"
        )

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
