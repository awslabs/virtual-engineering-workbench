import abc
import typing

from app.shared.adapters.boto import orchestration_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import repository_exception, unit_of_work

T = typing.TypeVar("T", bound="Aggregate")


def get_dict_difference(new_dict: dict, old_dict: dict) -> dict:
    updated_attrs = {}
    for key, value in new_dict.items():
        if value != old_dict.get(key):
            updated_attrs[key] = value
    return updated_attrs


class Aggregate(abc.ABC):
    def __init__(self):
        self._pending_events: list[tuple[message_bus.Message, message_bus.ScheduleConfig | None]] = []
        self._pending_updates: list[typing.Callable[[unit_of_work.UnitOfWork], None]] = []
        self._unscheduled_events: list[str] = []

    @property
    def pending_events(self) -> list[tuple[message_bus.Message, message_bus.ScheduleConfig]]:
        """Returns all the pending events of the aggregate"""
        return self._pending_events

    @property
    def pending_updates(self) -> list[typing.Callable[[unit_of_work.UnitOfWork], None]]:
        """Returns all the repository update actions for the unit of work"""
        return self._pending_updates

    @property
    def unscheduled_events(self) -> list[str]:
        """Returns all the pending unschelued event guids"""
        return self._unscheduled_events

    def _publish(self, event: message_bus.Message, schedule_config: message_bus.ScheduleConfig | None = None):
        self._repository_actions()
        self._pending_events.append((event, schedule_config))

    def _unschedule(self, event_guid: str):
        self._unscheduled_events.append(event_guid)

    @abc.abstractmethod
    def _repository_actions(self): ...


class AggregateRepository(typing.Generic[T], abc.ABC):

    @abc.abstractmethod
    def save(self, aggregate: T): ...


class IAggregatePublisher(abc.ABC):

    @abc.abstractmethod
    def publish(self, aggregate: Aggregate): ...


class AggregatePublisher(IAggregatePublisher):
    def __init__(
        self,
        uow: unit_of_work.UnitOfWork,
        mb: message_bus.MessageBus,
    ):
        self.__uow = uow
        self.__message_bus = mb

    def publish(self, aggregate: Aggregate):
        with self.__uow:
            if aggregate.pending_updates:
                for update in aggregate.pending_updates:
                    update(self.__uow)
                self.__uow.commit()

            if aggregate.pending_events:
                for event, schedule_config in aggregate.pending_events:
                    if schedule_config:
                        self.__message_bus.publish(event, schedule_config)
                    else:
                        self.__message_bus.publish(event)

            if aggregate.unscheduled_events:
                for event_guid in aggregate.unscheduled_events:
                    self.__message_bus.unschedule(event_guid)

    @property
    def uow(self):
        return self.__uow

    @property
    def mb(self):
        return self.__message_bus


class AggregateRepositoryPublisher(IAggregatePublisher):
    def __init__(self, mb: message_bus.MessageBus):
        self.__mb = mb
        self.__repositories: dict[type, AggregateRepository] = {}

    def with_repository(self, repository: AggregateRepository) -> typing.Self:
        aggregate_type = repository.__class__.__orig_bases__[0].__args__[0]
        self.__repositories[aggregate_type] = repository
        return self

    def publish(self, aggregate: Aggregate):
        aggregate_type = type(aggregate)
        if aggregate_type in self.__repositories:
            self.__repositories[aggregate_type].save(aggregate)
        else:
            raise repository_exception.RepositoryException(f"Repository for {aggregate_type.__name__} not found")

        for event, schedule_config in aggregate.pending_events:
            if schedule_config:
                self.__mb.publish(event, schedule_config)
            else:
                self.__mb.publish(event)

            for event_guid in aggregate.unscheduled_events:
                self.__mb.unschedule(event_guid)


class OrchestratedAggregatePublisherDecorator(IAggregatePublisher):

    def __init__(
        self,
        inner: IAggregatePublisher,
        os: orchestration_service.OrchestrationService,
    ):
        self.__inner = inner
        self.__orchestration_service = os

    def publish(self, aggregate: Aggregate):

        self.__inner.publish(aggregate)

        for event, _ in aggregate.pending_events:

            if isinstance(event, message_bus.SuccessMessage):
                self.__orchestration_service.send_callback_success(
                    callback_token=event.orchestrator_callback_token,
                    result={
                        "domain-event": event.__class__.__name__,
                        "result": event.dict(by_alias=True),
                    },
                )

            if isinstance(event, message_bus.FailureMessage):
                self.__orchestration_service.send_callback_failure(
                    callback_token=event.orchestrator_callback_token,
                    error_type=event.orchestrator_error_type,
                    error_message=event.orchestrator_error_message,
                )
