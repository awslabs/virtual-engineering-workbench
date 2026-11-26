import logging
from unittest import mock

import assertpy
import pytest

from app.packaging.domain.command_handlers.marketplace import cancel_agreement_command_handler, event_publication
from app.packaging.domain.exceptions.marketplace_conflict_exception import MarketplaceConflictException
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.shared.instrumentation import metrics


def _call_handle(cmd, procurement_mock, msg_bus_mock, metrics_mock=None, agreement_mock=None):
    return cancel_agreement_command_handler.handle(
        command=cmd,
        procurement_svc=procurement_mock,
        agreement_svc=agreement_mock or mock.create_autospec(spec=MarketplaceAgreementService),
        msg_bus=msg_bus_mock,
        logger=logging.getLogger("test"),
        metrics_client=metrics_mock,
    )


def test_handle_should_cancel_agreement_and_publish_event(
    procurement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    # ARRANGE
    cmd = get_test_cancel_agreement_command()

    # ACT
    _call_handle(cmd, procurement_service_mock, message_bus_mock)

    # ASSERT
    procurement_service_mock.cancel_agreement.assert_called_once_with("agmt-1234567890abc")
    message_bus_mock.publish.assert_called_once()
    (event,), _ = message_bus_mock.publish.call_args
    assertpy.assert_that(event.agreementId).is_equal_to("agmt-1234567890abc")
    # No projectId on the event: a Marketplace agreement is an account-level
    # resource with no project dimension to validate a projectId against.
    assertpy.assert_that(hasattr(event, "projectId")).is_false()


def test_handle_should_propagate_adapter_exception_from_service(
    procurement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    from app.packaging.adapters.exceptions.adapter_exception import AdapterException

    # ARRANGE
    procurement_service_mock.cancel_agreement.side_effect = AdapterException("boom")
    cmd = get_test_cancel_agreement_command()

    # ACT / ASSERT
    with pytest.raises(AdapterException):
        _call_handle(cmd, procurement_service_mock, message_bus_mock)
    message_bus_mock.publish.assert_not_called()


# ---------------------------------------------------------------------
# Publication failure. Once CancelAgreement returns, the agreement is
# cancelled in AWS, so a publish failure must not surface as a failed
# cancellation.
# ---------------------------------------------------------------------


def test_handle_should_not_raise_when_publication_fails(
    procurement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    """The agreement is already cancelled in AWS; the caller must be told so."""
    # ARRANGE
    cmd = get_test_cancel_agreement_command()
    message_bus_mock.publish.side_effect = RuntimeError("event bus unavailable")

    # ACT / ASSERT — must not raise
    _call_handle(cmd, procurement_service_mock, message_bus_mock)

    procurement_service_mock.cancel_agreement.assert_called_once_with("agmt-1234567890abc")


def test_handle_should_still_propagate_a_failed_cancellation(
    procurement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    """Calibration: absorbing publish failures must not absorb AWS failures.

    If CancelAgreement itself fails, nothing was cancelled and the caller
    must hear about it.
    """
    from app.packaging.adapters.exceptions.adapter_exception import AdapterException

    # ARRANGE
    cmd = get_test_cancel_agreement_command()
    procurement_service_mock.cancel_agreement.side_effect = AdapterException("denied")

    # ACT / ASSERT
    with pytest.raises(AdapterException):
        _call_handle(cmd, procurement_service_mock, message_bus_mock)

    message_bus_mock.publish.assert_not_called()


def test_handle_should_emit_a_metric_when_publication_fails(
    procurement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    # ARRANGE
    message_bus_mock.publish.side_effect = RuntimeError("event bus unavailable")
    metrics_mock = mock.create_autospec(spec=metrics.Metrics)

    # ACT
    _call_handle(get_test_cancel_agreement_command(), procurement_service_mock, message_bus_mock, metrics_mock)

    # ASSERT
    metrics_mock.publish_counter.assert_called_once_with(
        metric_name=event_publication.PUBLISH_FAILED_METRIC,
        metric_type=metrics.MetricType.FailedCommand,
    )


# ---------------------------------------------------------------------
# Replay. AWS rejects cancelling an already-cancelled agreement with
# ConflictException. When the agreement's status is CANCELLED, the retry is
# the same cancellation and must succeed; any other status means the
# conflict is real (for example an agreement not eligible for cancellation).
# ---------------------------------------------------------------------


def test_handle_should_succeed_when_called_twice(
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    # ARRANGE — AWS cancels once, then reports the conflict on the replay
    procurement_service_mock.cancel_agreement.side_effect = [None, MarketplaceConflictException("already cancelled")]
    agreement_service_mock.get_agreement_status.return_value = "CANCELLED"
    cmd = get_test_cancel_agreement_command()

    # ACT
    first = _call_handle(cmd, procurement_service_mock, message_bus_mock, agreement_mock=agreement_service_mock)
    second = _call_handle(cmd, procurement_service_mock, message_bus_mock, agreement_mock=agreement_service_mock)

    # ASSERT
    assertpy.assert_that(second).is_equal_to(first)
    agreement_service_mock.get_agreement_status.assert_called_once_with("agmt-1234567890abc")
    published = [call.args[0] for call in message_bus_mock.publish.call_args_list]
    assertpy.assert_that([e.agreementId for e in published]).is_equal_to(["agmt-1234567890abc"] * 2)


def test_handle_should_publish_the_event_on_a_replay_after_a_lost_event(
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    # ARRANGE
    procurement_service_mock.cancel_agreement.side_effect = [None, MarketplaceConflictException("already cancelled")]
    agreement_service_mock.get_agreement_status.return_value = "CANCELLED"
    message_bus_mock.publish.side_effect = [RuntimeError("event bus unavailable"), None]
    cmd = get_test_cancel_agreement_command()

    # ACT
    _call_handle(cmd, procurement_service_mock, message_bus_mock, agreement_mock=agreement_service_mock)
    _call_handle(cmd, procurement_service_mock, message_bus_mock, agreement_mock=agreement_service_mock)

    # ASSERT
    assertpy.assert_that(message_bus_mock.publish.call_count).is_equal_to(2)


@pytest.mark.parametrize("status", ["ACTIVE", "EXPIRED", "TERMINATED", "REPLACED"])
def test_handle_should_raise_a_conflict_when_the_agreement_is_not_cancelled(
    status,
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    # ARRANGE
    conflict = MarketplaceConflictException("not eligible for cancellation")
    procurement_service_mock.cancel_agreement.side_effect = conflict
    agreement_service_mock.get_agreement_status.return_value = status

    # ACT / ASSERT
    with pytest.raises(MarketplaceConflictException) as exc_info:
        _call_handle(
            get_test_cancel_agreement_command(),
            procurement_service_mock,
            message_bus_mock,
            agreement_mock=agreement_service_mock,
        )
    assertpy.assert_that(exc_info.value).is_same_as(conflict)
    message_bus_mock.publish.assert_not_called()


def test_handle_should_raise_the_conflict_when_the_agreement_cannot_be_described(
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    # ARRANGE
    conflict = MarketplaceConflictException("already cancelled")
    procurement_service_mock.cancel_agreement.side_effect = conflict
    agreement_service_mock.get_agreement_status.side_effect = RuntimeError("DescribeAgreement denied")

    # ACT / ASSERT
    with pytest.raises(MarketplaceConflictException) as exc_info:
        _call_handle(
            get_test_cancel_agreement_command(),
            procurement_service_mock,
            message_bus_mock,
            agreement_mock=agreement_service_mock,
        )
    assertpy.assert_that(exc_info.value).is_same_as(conflict)
    message_bus_mock.publish.assert_not_called()


def test_handle_should_not_check_status_for_non_conflict_failures(
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    from app.packaging.adapters.exceptions.adapter_exception import AdapterException

    # ARRANGE
    procurement_service_mock.cancel_agreement.side_effect = AdapterException("throttled")

    # ACT / ASSERT
    with pytest.raises(AdapterException):
        _call_handle(
            get_test_cancel_agreement_command(),
            procurement_service_mock,
            message_bus_mock,
            agreement_mock=agreement_service_mock,
        )
    agreement_service_mock.get_agreement_status.assert_not_called()


def test_handle_should_refuse_to_cancel_a_non_ami_agreement(
    procurement_service_mock,
    message_bus_mock,
    get_test_cancel_agreement_command,
):
    from app.packaging.domain.exceptions.domain_exception import DomainException

    # ARRANGE — the hub account also holds a SaaS agreement
    agreement_mock = mock.create_autospec(spec=MarketplaceAgreementService)
    agreement_mock.is_ami_agreement.return_value = False

    # ACT / ASSERT
    with pytest.raises(DomainException, match="not an AMI agreement"):
        _call_handle(
            get_test_cancel_agreement_command(),
            procurement_service_mock,
            message_bus_mock,
            agreement_mock=agreement_mock,
        )
    procurement_service_mock.cancel_agreement.assert_not_called()
    message_bus_mock.publish.assert_not_called()
