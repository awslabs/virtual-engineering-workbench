from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ScheduleConfig(BaseModel):
    end_time: datetime = Field(..., alias="EndTime")
    schedule_id: str = Field(..., alias="ScheduleId")


class ScheduleFlexibleConfig(BaseModel):
    end_time: datetime = Field(..., alias="EndTime")
    schedule_id: str = Field(..., alias="ScheduleId")
    flexible_time_window: bool = Field(..., alias="FlexibleTimeWindow")
    cron_expression: Optional[str] = Field(None, alias="CronExpression")


class EventContext(BaseModel):
    event_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), alias="EventTime")


class Message(BaseModel, ABC):
    event_name: str = Field(..., alias="eventName", json_schema_extra={"name": "Event Name"})
    event_context: EventContext = Field(default_factory=lambda: EventContext(), alias="context")


class SuccessMessage(Message, ABC):
    orchestrator_callback_token: str = Field(..., alias="orchestratorCallbackToken", exclude=True)
    orchestrator_result: dict = Field({}, alias="orchestratorResult", exclude=True)


class FailureMessage(Message, ABC):
    orchestrator_callback_token: str = Field(..., alias="orchestratorCallbackToken", exclude=True)
    orchestrator_error_type: str = Field(..., alias="orchestratorErrorType", exclude=True)
    orchestrator_error_message: str = Field(..., alias="orchestratorErrorMessage", exclude=True)


class MessageBus(ABC):
    @abstractmethod
    def publish(
        self,
        message: Message,
        schedule_config: Optional[ScheduleConfig] = None,
        flexible_config: Optional[ScheduleFlexibleConfig] = None,
    ) -> None: ...

    @abstractmethod
    def reschedule(
        self,
        message: Message,
        schedule_config: Optional[ScheduleConfig] = None,
        flexible_config: Optional[ScheduleFlexibleConfig] = None,
    ) -> None: ...

    @abstractmethod
    def unschedule(self, schedule_id: str) -> None: ...
