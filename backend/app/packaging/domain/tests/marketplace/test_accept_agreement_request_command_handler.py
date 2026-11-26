import logging
from unittest import mock

import assertpy
import pytest

from app.packaging.domain.command_handlers.marketplace import (
    accept_agreement_request_command_handler,
    event_publication,
)
from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.exceptions.marketplace_conflict_exception import MarketplaceConflictException
from app.packaging.domain.read_models.agreement_request import AcceptedAgreement
from app.shared.instrumentation import metrics


def _call_handle(cmd, procurement_mock, msg_bus_mock, metrics_mock=None):
    return accept_agreement_request_command_handler.handle(
        command=cmd,
        procurement_svc=procurement_mock,
        msg_bus=msg_bus_mock,
        logger=logging.getLogger("test"),
        metrics_client=metrics_mock,
    )


def test_handle_should_accept_agreement_request_and_return_agreement_id(
    procurement_service_mock,
    message_bus_mock,
    get_test_accept_agreement_request_command,
    get_test_accepted_agreement,
):
    # ARRANGE
    procurement_service_mock.accept_agreement_request.return_value = get_test_accepted_agreement()
    cmd = get_test_accept_agreement_request_command()

    # ACT
    result = _call_handle(cmd, procurement_service_mock, message_bus_mock)

    # ASSERT
    assertpy.assert_that(result).is_equal_to("agmt-1234567890abc")
    procurement_service_mock.accept_agreement_request.assert_called_once_with("ar-1234567890abc")
    message_bus_mock.publish.assert_called_once()
    (event,), _ = message_bus_mock.publish.call_args
    assertpy.assert_that(event.agreementId).is_equal_to("agmt-1234567890abc")
    assertpy.assert_that(event.agreementRequestId).is_equal_to("ar-1234567890abc")


# ---------------------------------------------------------------------
# Publication failure. Once AcceptAgreementRequest returns, the acceptance
# is final in AWS. A failure to publish the domain event afterwards must
# therefore NOT be reported to the caller as a failed acceptance.
# ---------------------------------------------------------------------


def test_handle_should_return_agreement_id_when_publication_fails(
    procurement_service_mock,
    message_bus_mock,
    get_test_accept_agreement_request_command,
    get_test_accepted_agreement,
):
    """The acceptance succeeded in AWS; the caller must be told so.

    Propagating the publish error would show the user a 500 for a purchase
    that actually went through.
    """
    # ARRANGE
    cmd = get_test_accept_agreement_request_command()
    procurement_service_mock.accept_agreement_request.return_value = get_test_accepted_agreement()
    message_bus_mock.publish.side_effect = RuntimeError("event bus unavailable")

    # ACT
    result = _call_handle(cmd, procurement_service_mock, message_bus_mock)

    # ASSERT
    assertpy.assert_that(result).is_equal_to("agmt-1234567890abc")


def test_handle_should_emit_a_metric_when_publication_fails(
    procurement_service_mock,
    message_bus_mock,
    get_test_accept_agreement_request_command,
    get_test_accepted_agreement,
):
    """A dropped event must be detectable rather than silent."""
    # ARRANGE
    cmd = get_test_accept_agreement_request_command()
    procurement_service_mock.accept_agreement_request.return_value = get_test_accepted_agreement()
    message_bus_mock.publish.side_effect = RuntimeError("event bus unavailable")
    metrics_mock = mock.create_autospec(spec=metrics.Metrics)

    # ACT
    _call_handle(cmd, procurement_service_mock, message_bus_mock, metrics_mock=metrics_mock)

    # ASSERT
    metrics_mock.publish_counter.assert_called_once_with(
        metric_name=event_publication.PUBLISH_FAILED_METRIC,
        metric_type=metrics.MetricType.FailedCommand,
    )


def test_handle_should_not_emit_the_failure_metric_on_success(
    procurement_service_mock,
    message_bus_mock,
    get_test_accept_agreement_request_command,
    get_test_accepted_agreement,
):
    """Calibration: the failure metric must not fire on the happy path."""
    # ARRANGE
    cmd = get_test_accept_agreement_request_command()
    procurement_service_mock.accept_agreement_request.return_value = get_test_accepted_agreement()
    metrics_mock = mock.create_autospec(spec=metrics.Metrics)

    # ACT
    _call_handle(cmd, procurement_service_mock, message_bus_mock, metrics_mock=metrics_mock)

    # ASSERT
    metrics_mock.publish_counter.assert_not_called()


# ---------------------------------------------------------------------
# Replay. AWS rejects a second AcceptAgreementRequest for the same request
# with ConflictException. AWS cannot map a request to the agreement it
# created, so a conflict is never reported as a successful acceptance: the
# buyer gets a refusal (HTTP 400) telling them to check the Agreements page.
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "conflict",
    [
        MarketplaceConflictException("already accepted", resource_type="Agreement", resource_id="agmt-other"),
        MarketplaceConflictException("request expired", resource_type="AgreementRequest", resource_id="ar-1"),
        MarketplaceConflictException("conflict without a resource"),
    ],
)
def test_handle_should_refuse_a_conflicting_accept_without_reporting_success(
    conflict,
    procurement_service_mock,
    message_bus_mock,
    get_test_accept_agreement_request_command,
):
    """Even when AWS names an agreement, it may belong to another purchase of
    the same offer; returning it would report a purchase that did not happen."""
    # ARRANGE
    procurement_service_mock.accept_agreement_request.side_effect = conflict
    cmd = get_test_accept_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(domain_exception.DomainException) as exc_info:
        _call_handle(cmd, procurement_service_mock, message_bus_mock)
    assertpy.assert_that(str(exc_info.value)).contains("ar-1234567890abc").contains("Agreements page")
    assertpy.assert_that(exc_info.value.__cause__).is_same_as(conflict)
    message_bus_mock.publish.assert_not_called()


def test_handle_should_refuse_the_second_of_two_identical_calls(
    procurement_service_mock,
    message_bus_mock,
    get_test_accept_agreement_request_command,
):
    # ARRANGE — AWS accepts once, then reports the conflict on the replay
    procurement_service_mock.accept_agreement_request.side_effect = [
        AcceptedAgreement(agreementId="agmt-1234567890abc"),
        MarketplaceConflictException("already accepted", resource_type="Agreement", resource_id="agmt-1234567890abc"),
    ]
    cmd = get_test_accept_agreement_request_command()

    # ACT
    first = _call_handle(cmd, procurement_service_mock, message_bus_mock)
    with pytest.raises(domain_exception.DomainException):
        _call_handle(cmd, procurement_service_mock, message_bus_mock)

    # ASSERT — one acceptance, one event
    assertpy.assert_that(first).is_equal_to("agmt-1234567890abc")
    assertpy.assert_that(procurement_service_mock.accept_agreement_request.call_count).is_equal_to(2)
    message_bus_mock.publish.assert_called_once()


def test_handle_should_propagate_non_conflict_failures(
    procurement_service_mock,
    message_bus_mock,
    get_test_accept_agreement_request_command,
):
    # ARRANGE
    procurement_service_mock.accept_agreement_request.side_effect = RuntimeError("throttled")
    cmd = get_test_accept_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(RuntimeError):
        _call_handle(cmd, procurement_service_mock, message_bus_mock)
    message_bus_mock.publish.assert_not_called()
