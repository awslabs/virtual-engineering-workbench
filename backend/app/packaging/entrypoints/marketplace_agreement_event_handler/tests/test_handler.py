from decimal import Decimal

import assertpy
import pytest

from app.packaging.domain.commands.marketplace import (
    observe_marketplace_agreement_activated_command,
    observe_marketplace_agreement_amended_command,
    observe_marketplace_agreement_ended_command,
    observe_marketplace_agreement_ending_soon_command,
    observe_marketplace_agreement_renewal_terms_finalized_command,
    observe_marketplace_agreement_renewal_upcoming_command,
)
from app.packaging.entrypoints.marketplace_agreement_event_handler.tests.conftest import GlobalVariables
from app.shared.middleware.event_handler import EventResolverException


def _install_mock_bus(mocked_bus):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.dependencies.command_bus = mocked_bus


def test_created_new_dispatches_activated_command(lambda_context, created_new_event, mocked_command_bus):
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    _install_mock_bus(mocked_command_bus)

    handler.handler(created_new_event(), lambda_context)

    mocked_command_bus.handle.assert_called_once()
    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched).is_instance_of(
        observe_marketplace_agreement_activated_command.ObserveMarketplaceAgreementActivatedCommand
    )
    assertpy.assert_that(dispatched.agreementId.value).is_equal_to(GlobalVariables.TEST_AGREEMENT_ID.value)
    assertpy.assert_that(dispatched.offerId.value).is_equal_to(GlobalVariables.TEST_OFFER_ID.value)
    assertpy.assert_that(dispatched.intent).is_equal_to("NEW")
    assertpy.assert_that(dispatched.status).is_equal_to("ACTIVE")
    assertpy.assert_that(dispatched.productId).is_none()
    assertpy.assert_that(dispatched.previousAgreementId).is_none()
    assertpy.assert_that(dispatched.proposerAccountId).is_equal_to(GlobalVariables.TEST_PROPOSER_ACCOUNT.value)
    assertpy.assert_that(dispatched.acceptorAccountId).is_equal_to(GlobalVariables.TEST_ACCEPTOR_ACCOUNT.value)


def test_created_renew_carries_previous_agreement_and_product(lambda_context, created_renew_event, mocked_command_bus):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(created_renew_event(), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.intent).is_equal_to("RENEW")
    assertpy.assert_that(dispatched.previousAgreementId).is_equal_to(GlobalVariables.TEST_AGREEMENT_ID.value)
    assertpy.assert_that(dispatched.productId).is_equal_to(GlobalVariables.TEST_PRODUCT_ID.value)


def test_created_without_intent_dispatches_command_with_none_intent(
    lambda_context, created_new_event, mocked_command_bus
):
    """If AWS ever drops the ``intent`` field on a Created event, pass
    ``None`` through rather than silently emitting ``intent=""``.
    Downstream subscribers can explicitly handle ``None`` (e.g. warn +
    default-branch) instead of falling through a switch on
    empty-string."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = created_new_event()
    evt["detail"]["agreement"].pop("intent")

    handler.handler(evt, lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.intent).is_none()


def test_amended_dispatches_amended_command(lambda_context, amended_event, mocked_command_bus):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(amended_event(), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched).is_instance_of(
        observe_marketplace_agreement_amended_command.ObserveMarketplaceAgreementAmendedCommand
    )
    assertpy.assert_that(dispatched.autoRenewalEnabled).is_true()
    assertpy.assert_that(dispatched.autoRenewalDisabledBy).is_equal_to("ACCEPTOR")
    assertpy.assert_that(dispatched.lockoutStartTime).is_equal_to("2025-05-20T21:36:03Z")


def test_ended_cancelled_dispatches_ended_command(lambda_context, ended_event, mocked_command_bus):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(ended_event("CANCELLED"), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched).is_instance_of(
        observe_marketplace_agreement_ended_command.ObserveMarketplaceAgreementEndedCommand
    )
    assertpy.assert_that(dispatched.status).is_equal_to("CANCELLED")


@pytest.mark.parametrize("status", ["CANCELLED", "EXPIRED", "TERMINATED", "RENEWED", "REPLACED"])
def test_ended_accepts_all_five_end_reasons(lambda_context, ended_event, mocked_command_bus, status):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(ended_event(status), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.status).is_equal_to(status)


def test_ending_180_days_dispatches_ending_soon_command(lambda_context, ending_event, mocked_command_bus):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(ending_event(180), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched).is_instance_of(
        observe_marketplace_agreement_ending_soon_command.ObserveMarketplaceAgreementEndingSoonCommand
    )
    assertpy.assert_that(dispatched.daysBeforeEndTime).is_equal_to(180)
    assertpy.assert_that(dispatched.endTime).is_equal_to("2025-05-30T21:36:03Z")


@pytest.mark.parametrize("days", [180, 120, 90, 60, 30])
def test_ending_accepts_all_five_buckets(lambda_context, ending_event, mocked_command_bus, days):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(ending_event(days), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.daysBeforeEndTime).is_equal_to(days)


@pytest.mark.parametrize("missing_field", ["daysBeforeEndTime", "endTime"])
def test_ending_missing_required_field_raises(lambda_context, ending_event, mocked_command_bus, missing_field):
    """Malformed AWS event (missing ``daysBeforeEndTime`` or ``endTime``)
    must raise so the Lambda error metric increments and the function's
    dead-letter queue captures the drift — a silent skip would let the entire buyer-side
    expiry-warning stream disappear unnoticed if AWS renamed a field."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = ending_event(180)
    evt["detail"]["agreement"].pop(missing_field)

    with pytest.raises(EventResolverException):
        handler.handler(evt, lambda_context)

    mocked_command_bus.handle.assert_not_called()


def test_renewal_terms_finalized_dispatches_command_with_decimal_tcv(
    lambda_context, renewal_terms_finalized_event, mocked_command_bus
):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(renewal_terms_finalized_event(), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched).is_instance_of(
        observe_marketplace_agreement_renewal_terms_finalized_command.ObserveMarketplaceAgreementRenewalTermsFinalizedCommand  # noqa: E501
    )
    assertpy.assert_that(dispatched.tcv).is_equal_to(Decimal("105000.00"))
    assertpy.assert_that(dispatched.currency).is_equal_to("USD")
    assertpy.assert_that(dispatched.termsFinalizedTime).is_equal_to("2025-05-15T21:36:03Z")
    assertpy.assert_that(dispatched.lockoutReached).is_false()


def test_renewal_terms_finalized_tolerates_unparseable_tcv(
    lambda_context, renewal_terms_finalized_event, mocked_command_bus
):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = renewal_terms_finalized_event()
    evt["detail"]["renewalSummary"]["tcv"] = "not-a-number"

    handler.handler(evt, lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.tcv).is_none()
    assertpy.assert_that(dispatched.currency).is_equal_to("USD")


def test_renewal_upcoming_dispatches_command_with_lockout_reached(
    lambda_context, renewal_upcoming_event, mocked_command_bus
):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(renewal_upcoming_event(), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched).is_instance_of(
        observe_marketplace_agreement_renewal_upcoming_command.ObserveMarketplaceAgreementRenewalUpcomingCommand
    )
    assertpy.assert_that(dispatched.lockoutReached).is_true()
    assertpy.assert_that(dispatched.tcv).is_equal_to(Decimal("105000.00"))


def test_renewal_terms_finalized_parses_without_agreement_status(
    lambda_context, renewal_terms_finalized_event, mocked_command_bus
):
    """AWS documented shape for 'Renewal Terms Finalized' events omits
    `detail.agreement.status`. Regression guard: making the shared
    AgreementBlock.status Optional lets these events parse and
    dispatch. If someone tightens it back to required, this fails."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = renewal_terms_finalized_event()
    # Belt-and-braces: even if the fixture drifts, this test asserts the
    # documented AWS shape (no `status`).
    evt["detail"]["agreement"].pop("status", None)

    handler.handler(evt, lambda_context)

    mocked_command_bus.handle.assert_called_once()


def test_renewal_upcoming_parses_without_agreement_status(lambda_context, renewal_upcoming_event, mocked_command_bus):
    """AWS documented shape for 'Renewal Upcoming' events omits
    `detail.agreement.status`. See sibling test above."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = renewal_upcoming_event()
    evt["detail"]["agreement"].pop("status", None)

    handler.handler(evt, lambda_context)

    mocked_command_bus.handle.assert_called_once()


# ---------------------------------------------------------------------
# product-null coverage — AWS omits `detail.product` on Amended, Ending,
# Renewal Terms Finalized, and Renewal Upcoming events in some cases.
# The handler guards each `.product` access with `if event.product else None`.
# These tests exercise that guard branch per event type.
# ---------------------------------------------------------------------


def test_amended_without_product_dispatches_command_with_none_product_id(
    lambda_context, amended_event, mocked_command_bus
):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = amended_event()
    evt["detail"].pop("product", None)

    handler.handler(evt, lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.productId).is_none()


def test_ending_without_product_dispatches_command_with_none_product_id(
    lambda_context, ending_event, mocked_command_bus
):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = ending_event(90)
    evt["detail"].pop("product", None)

    handler.handler(evt, lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.productId).is_none()


def test_renewal_terms_finalized_without_product_dispatches_command_with_none_product_id(
    lambda_context, renewal_terms_finalized_event, mocked_command_bus
):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = renewal_terms_finalized_event()
    evt["detail"].pop("product", None)

    handler.handler(evt, lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.productId).is_none()


def test_renewal_upcoming_without_product_dispatches_command_with_none_product_id(
    lambda_context, renewal_upcoming_event, mocked_command_bus
):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = renewal_upcoming_event()
    evt["detail"].pop("product", None)

    handler.handler(evt, lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.productId).is_none()


# ---------------------------------------------------------------------
# requestId / catalog propagation — regression guard so downstream
# idempotency (via requestId dedupe) and multi-catalog support don't
# get lost during future edits.
# ---------------------------------------------------------------------


def test_created_propagates_request_id_and_catalog(lambda_context, created_new_event, mocked_command_bus):
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(created_new_event(), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.requestId).is_equal_to(GlobalVariables.TEST_REQUEST_ID.value)
    assertpy.assert_that(dispatched.catalog).is_equal_to("AWSMarketplace")


def test_amended_propagates_intent(lambda_context, amended_event, mocked_command_bus):
    """AWS Amended events carry `intent=AMEND`. Regression guard: the
    handler must preserve it end-to-end so downstream subscribers can
    distinguish amendments from creations even if the domain event
    stream is replayed out of order."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    handler.handler(amended_event(), lambda_context)

    (dispatched,), _ = mocked_command_bus.handle.call_args
    assertpy.assert_that(dispatched.intent).is_equal_to("AMEND")


def test_unregistered_detail_type_raises_resolver_exception(lambda_context, created_new_event, mocked_command_bus):
    """Unknown ``detail-type`` must raise so Lambda retries it and then
    sends it to the function's dead-letter queue — silent drops hide
    integration drift."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    evt = created_new_event()
    evt["detail-type"] = "Purchase Agreement Renegotiation Started - Acceptor"

    with pytest.raises(EventResolverException):
        handler.handler(evt, lambda_context)

    mocked_command_bus.handle.assert_not_called()


# ---------------------------------------------------------------------
# AMI-only admission gate.
#
# The EventBridge rule cannot make this decision: it matches on `source`
# and `detail-type`, and no buyer-side event shape carries a product
# type (`detail.product` is `{id, title}`). So the gate calls
# DescribeAgreement. These tests cover drop, admit, and error-propagation
# for every event type.
# ---------------------------------------------------------------------


_ALL_EVENT_FIXTURES = [
    "created_new_event",
    "created_renew_event",
    "amended_event",
    "ended_event",
    "renewal_terms_finalized_event",
    "renewal_upcoming_event",
]


@pytest.mark.parametrize("fixture_name", _ALL_EVENT_FIXTURES)
def test_non_ami_agreement_is_not_republished(
    fixture_name, lambda_context, mocked_command_bus, ami_agreement_gate, request
):
    """A SaaS/Container/Data agreement event must not reach the domain bus."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    ami_agreement_gate.is_ami_agreement.return_value = False
    event = request.getfixturevalue(fixture_name)()

    handler.handler(event, lambda_context)

    mocked_command_bus.handle.assert_not_called()
    # The RENEW fixture carries its own new agreement id, so assert the
    # gate was asked about the id on the event rather than a fixed constant.
    ami_agreement_gate.is_ami_agreement.assert_called_once_with(event["detail"]["agreement"]["id"])


def test_non_ami_ending_event_is_dropped(lambda_context, ending_event, mocked_command_bus, ami_agreement_gate):
    """Ending's fixture takes an argument, so it gets its own test."""
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    ami_agreement_gate.is_ami_agreement.return_value = False

    handler.handler(ending_event(90), lambda_context)

    mocked_command_bus.handle.assert_not_called()


def test_non_ami_malformed_ending_event_is_dropped_not_raised(
    lambda_context, ending_event, mocked_command_bus, ami_agreement_gate
):
    """The gate runs before the malformed-event guard.

    A non-AMI Ending event missing `daysBeforeEndTime` is not ours, so it
    must drop quietly rather than raise and occupy the dead-letter queue.
    """
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    ami_agreement_gate.is_ami_agreement.return_value = False
    evt = ending_event(90)
    evt["detail"]["agreement"].pop("daysBeforeEndTime", None)

    handler.handler(evt, lambda_context)

    mocked_command_bus.handle.assert_not_called()


def test_describe_agreement_failure_propagates_rather_than_dropping(
    lambda_context, created_new_event, mocked_command_bus, ami_agreement_gate
):
    """An unknown product type must not be silently treated as non-AMI.

    If DescribeAgreement fails the type is unknown. Dropping would discard
    real AMI events for as long as an IAM misconfiguration lasted, with no
    error signal. The exception must surface so the event reaches the
    function's dead-letter queue after Lambda's retries.
    """
    from app.packaging.adapters.exceptions import adapter_exception
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    _install_mock_bus(mocked_command_bus)
    ami_agreement_gate.is_ami_agreement.side_effect = adapter_exception.AdapterException("denied")

    with pytest.raises(adapter_exception.AdapterException):
        handler.handler(created_new_event(), lambda_context)

    mocked_command_bus.handle.assert_not_called()


def test_ami_agreement_is_republished(lambda_context, created_new_event, mocked_command_bus, ami_agreement_gate):
    """Calibration: the gate must not over-filter.

    If this fails, the gate is dropping legitimate AMI traffic.
    """
    _install_mock_bus(mocked_command_bus)
    from app.packaging.entrypoints.marketplace_agreement_event_handler import handler

    ami_agreement_gate.is_ami_agreement.return_value = True

    handler.handler(created_new_event(), lambda_context)

    mocked_command_bus.handle.assert_called_once()
