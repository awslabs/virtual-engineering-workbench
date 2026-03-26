import logging
from typing import Optional

from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.message_bus.message_bus import Message, ScheduleConfig, ScheduleFlexibleConfig
from app.shared.instrumentation import metrics


class MessageBusMetrics(message_bus.MessageBus):
    def __init__(self, inner: message_bus.MessageBus, metrics_client: metrics.Metrics, logger: logging.Logger):
        self._inner = inner
        self._metrics = metrics_client
        self._logger = logger

    def publish(
        self,
        message: Message,
        schedule_config: Optional[ScheduleConfig] = None,
        flexible_config: Optional[ScheduleFlexibleConfig] = None,
    ) -> None:
        self._inner.publish(message, schedule_config=schedule_config, flexible_config=flexible_config)
        if schedule_config is None and flexible_config is None:
            try:
                self._metrics.publish_counter(
                    metric_name=message.event_name, metric_type=metrics.MetricType.DomainEvent
                )
            except Exception as e:
                self._logger.warning(f"Unable to publish metrics: {e}")
        else:
            try:
                self._metrics.publish_counter(
                    metric_name=f"{message.event_name}.schedule", metric_type=metrics.MetricType.DomainEvent
                )
            except Exception as e:
                self._logger.warning(f"Unable to publish metrics: {e}")

    def reschedule(self, message: Message, schedule_config: Optional[ScheduleConfig]) -> None:
        self._inner.reschedule(message, schedule_config)
        try:
            self._metrics.publish_counter(
                metric_name=f"{message.event_name}.reschedule", metric_type=metrics.MetricType.DomainEvent
            )
        except Exception as e:
            self._logger.warning(f"Unable to publish metrics: {e}")

    def unschedule(self, schedule_id: str) -> None:
        self._inner.unschedule(schedule_id)
        try:
            self._metrics.publish_counter(
                metric_name="DeleteEventScheduler", metric_type=metrics.MetricType.DomainEvent
            )
        except Exception as e:
            self._logger.warning(f"Unable to publish metrics: {e}")
