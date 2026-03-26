from unittest import mock

import pydantic
import pytest
from freezegun import freeze_time

from app.shared.adapters.boto import orchestration_service
from app.shared.adapters.message_bus import message_bus
from app.shared.adapters.unit_of_work_v2 import unit_of_work
from app.shared.ddd import aggregate


class DomainEvent(message_bus.Message):
    event_name: str = pydantic.Field("DomainEvent", alias="eventName", const=True)


class SuccessEvent(message_bus.SuccessMessage):
    event_name: str = pydantic.Field("SuccessEvent", alias="eventName", const=True)


class FailureEvent(message_bus.FailureMessage):
    event_name: str = pydantic.Field("FailureEvent", alias="eventName", const=True)


class TestAggregate(aggregate.Aggregate):

    def __init__(self):
        super().__init__()

    def do_stuff(self):
        self._publish(DomainEvent())

    def do_success(self):
        self._publish(SuccessEvent(orchestratorCallbackToken="test-token"))

    def do_failure(self):
        self._publish(
            FailureEvent(
                orchestratorCallbackToken="test-token",
                orchestratorErrorType="TestError",
                orchestratorErrorMessage="test error",
            )
        )

    def _repository_actions(self):
        self.pending_updates.append(
            lambda uow: uow.get_repository(unit_of_work.PrimaryKey, unit_of_work.Entity).remove(unit_of_work.PrimaryKey)
        )


class TestAggregateRepository(aggregate.AggregateRepository[TestAggregate]):
    def save(self, aggregate: TestAggregate):
        pass


@pytest.fixture(autouse=True)
def frozen_time():
    with freeze_time("2025-01-01 12:00:00"):
        yield


@pytest.fixture
def mock_uow():
    return mock.create_autospec(spec=unit_of_work.UnitOfWork)


@pytest.fixture
def mock_mb():
    return mock.create_autospec(spec=message_bus.MessageBus)


@pytest.fixture
def mock_os():
    return mock.create_autospec(spec=orchestration_service.OrchestrationService)


@pytest.fixture
def mock_agg_repository():
    return mock.create_autospec(spec=TestAggregateRepository)


def test_aggregate_publisher_when_has_events_should_publish(mock_uow, mock_mb):
    # ARRANGE
    publisher = aggregate.AggregatePublisher(uow=mock_uow, mb=mock_mb)

    agg = TestAggregate()
    agg.do_stuff()

    # ACT
    publisher.publish(agg)

    # ASSERT
    mock_mb.publish.assert_called_once_with(DomainEvent())


def test_aggregate_publisher_when_has_db_changes_should_save(mock_uow, mock_mb):
    # ARRANGE
    publisher = aggregate.AggregatePublisher(uow=mock_uow, mb=mock_mb)

    agg = TestAggregate()
    agg.do_stuff()

    # ACT
    publisher.publish(agg)

    # ASSERT
    mock_uow.commit.assert_called_once()


def test_orchestrated_aggregate_publisher_when_has_sucess_events_should_send_success_callback(
    mock_uow, mock_mb, mock_os
):
    # ARRANGE
    publisher = aggregate.OrchestratedAggregatePublisherDecorator(
        inner=aggregate.AggregatePublisher(uow=mock_uow, mb=mock_mb), os=mock_os
    )

    agg = TestAggregate()
    agg.do_success()

    # ACT
    publisher.publish(agg)

    # ASSERT
    mock_os.send_callback_success.assert_called_once_with(
        callback_token="test-token",
        result={
            "domain-event": "SuccessEvent",
            "result": {"context": {"EventTime": "2025-01-01T12:00:00+00:00"}, "eventName": "SuccessEvent"},
        },
    )
    mock_os.send_callback_failure.assert_not_called()


def test_orchestrated_aggregate_publisher_when_has_failure_events_should_send_failure_callback(
    mock_uow, mock_mb, mock_os
):
    # ARRANGE
    publisher = aggregate.OrchestratedAggregatePublisherDecorator(
        inner=aggregate.AggregatePublisher(uow=mock_uow, mb=mock_mb), os=mock_os
    )

    agg = TestAggregate()
    agg.do_failure()

    # ACT
    publisher.publish(agg)

    # ASSERT
    mock_os.send_callback_failure.assert_called_once_with(
        callback_token="test-token", error_type="TestError", error_message="test error"
    )
    mock_os.send_callback_success.assert_not_called()


def test_aggregate_repository_publisher_when_has_events_should_publish(mock_mb, mock_agg_repository):
    # ARRANGE
    publisher = aggregate.AggregateRepositoryPublisher(mb=mock_mb).with_repository(mock_agg_repository)

    agg = TestAggregate()
    agg.do_stuff()

    # ACT
    publisher.publish(agg)

    # ASSERT
    mock_agg_repository.save.assert_called_once_with(agg)
    mock_mb.publish.assert_called_once_with(DomainEvent())
