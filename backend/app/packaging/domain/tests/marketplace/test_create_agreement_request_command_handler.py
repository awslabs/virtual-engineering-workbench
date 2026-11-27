import assertpy
import pytest

from app.packaging.domain.command_handlers.marketplace import create_agreement_request_command_handler
from app.packaging.domain.exceptions.domain_exception import DomainException
from app.packaging.domain.read_models.marketplace_offer import MarketplaceOfferProductAssociation


def _call_handle(cmd, offer_discovery_mock, procurement_mock, msg_bus_mock, agreement_mock=None, metrics_mock=None):
    import logging
    from unittest import mock as _mock

    from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService

    if agreement_mock is None:
        agreement_mock = _mock.create_autospec(spec=MarketplaceAgreementService)
        agreement_mock.list_active_agreements.return_value = []
    return create_agreement_request_command_handler.handle(
        command=cmd,
        offer_discovery_svc=offer_discovery_mock,
        procurement_svc=procurement_mock,
        agreement_svc=agreement_mock,
        msg_bus=msg_bus_mock,
        logger=logging.getLogger("test"),
        metrics_client=metrics_mock,
    )


def test_handle_should_create_agreement_request_and_return_id(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd = get_test_create_agreement_request_command()

    # ACT
    result = _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    assertpy.assert_that(result.agreementRequestId).is_equal_to("ar-1234567890abc")
    _, kwargs = procurement_service_mock.create_agreement_request.call_args
    assertpy.assert_that(kwargs["agreement_proposal_identifier"]).is_equal_to("at-proposal1")
    assertpy.assert_that(kwargs["requested_terms"]).is_equal_to([{"id": "term-usage-1"}, {"id": "term-legal-1"}])
    assertpy.assert_that(kwargs["client_token"]).is_not_none()
    message_bus_mock.publish.assert_called_once()
    (event,), _ = message_bus_mock.publish.call_args
    assertpy.assert_that(event.agreementRequestId).is_equal_to("ar-1234567890abc")
    assertpy.assert_that(event.offerId).is_equal_to("offer-abc123")
    assertpy.assert_that(event.agreementProposalId).is_equal_to("at-proposal1")


def test_handle_should_forward_supplied_client_token(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """When the caller supplies a clientToken, it must be forwarded verbatim
    so retries under the buyer's idempotency key succeed."""
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd = get_test_create_agreement_request_command()
    cmd.clientToken = "caller-idempotency-key-42"

    # ACT
    _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    _, kwargs = procurement_service_mock.create_agreement_request.call_args
    assertpy.assert_that(kwargs["client_token"]).is_equal_to("caller-idempotency-key-42")


def test_handle_should_raise_when_no_requested_terms(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
):
    # ARRANGE
    cmd = get_test_create_agreement_request_command(requested_terms=[])

    # ACT / ASSERT
    with pytest.raises(DomainException, match="At least one requested term"):
        _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    procurement_service_mock.create_agreement_request.assert_not_called()
    offer_discovery_service_mock.get_offer.assert_not_called()


def test_handle_should_raise_when_offer_has_no_products(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
):
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer(associated_products=[])
    cmd = get_test_create_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(DomainException, match="no associated products"):
        _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    procurement_service_mock.create_agreement_request.assert_not_called()


def test_handle_should_reject_offer_that_is_part_of_offer_set(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
):
    # ARRANGE — bundle offer.
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer(
        associated_products=[
            MarketplaceOfferProductAssociation(productId="prod-bundle-1", partOfOfferSet=True),
        ]
    )
    cmd = get_test_create_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(DomainException, match="multi-product offer set"):
        _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    procurement_service_mock.create_agreement_request.assert_not_called()


def test_handle_should_reject_offer_with_multiple_products(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
):
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer(
        associated_products=[
            MarketplaceOfferProductAssociation(productId="prod-1"),
            MarketplaceOfferProductAssociation(productId="prod-2"),
        ]
    )
    cmd = get_test_create_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(DomainException, match="single-product AMI offers"):
        _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    procurement_service_mock.create_agreement_request.assert_not_called()


def test_handle_should_reject_non_ami_product(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
):
    # ARRANGE — offer looks single-product but the product is a SaaS entry.
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details(
        fulfillment_option_types=["SAAS"]
    )
    cmd = get_test_create_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(DomainException, match="not an AMI product"):
        _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    procurement_service_mock.create_agreement_request.assert_not_called()


def test_handle_should_emit_charge_summary_in_event(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    # ARRANGE
    from decimal import Decimal

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote(
        new_agreement_value="199.99", new_agreement_value_after_tax="219.99", currency="EUR"
    )
    cmd = get_test_create_agreement_request_command()

    # ACT
    _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    (event,), _ = message_bus_mock.publish.call_args
    assertpy.assert_that(event.estimatedAgreementValue).is_equal_to(Decimal("199.99"))
    assertpy.assert_that(event.estimatedAgreementValueAfterTax).is_equal_to(Decimal("219.99"))
    assertpy.assert_that(event.estimatedCurrencyCode).is_equal_to("EUR")


def test_handle_should_emit_null_charge_fields_when_charge_summary_omitted(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """Pure usage-based pricing paths leave chargeSummary absent. The
    event's estimated fields must be None rather than missing entirely so
    downstream consumers get a stable schema."""
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote(
        new_agreement_value=None, new_agreement_value_after_tax=None, currency=None
    )
    cmd = get_test_create_agreement_request_command()

    # ACT
    _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    (event,), _ = message_bus_mock.publish.call_args
    assertpy.assert_that(event.estimatedAgreementValue).is_none()
    assertpy.assert_that(event.estimatedAgreementValueAfterTax).is_none()
    assertpy.assert_that(event.estimatedCurrencyCode).is_none()


def test_handle_should_derive_a_stable_client_token_when_none_supplied(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """Two invocations of the SAME purchase intent must carry the SAME token.

    A fresh token per call would make a replay create a SECOND agreement
    request, because AWS keys idempotency on clientToken.
    """
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd_a = get_test_create_agreement_request_command()
    cmd_b = get_test_create_agreement_request_command()

    # ACT
    _call_handle(cmd_a, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    _call_handle(cmd_b, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    call_a_kwargs = procurement_service_mock.create_agreement_request.call_args_list[0].kwargs
    call_b_kwargs = procurement_service_mock.create_agreement_request.call_args_list[1].kwargs
    assertpy.assert_that(call_a_kwargs["client_token"]).is_equal_to(call_b_kwargs["client_token"])


def test_derived_client_token_ignores_requested_term_ordering(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """The same term SET in a different order is the same purchase.

    AWS raises ConflictException when a token is reused with a payload
    differing in list order, and the wizard builds this list by filtering
    the offer's terms -- an order that is not guaranteed stable. The token
    must therefore depend on the set, not the sequence.
    """
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd_a = get_test_create_agreement_request_command(requested_terms=[{"id": "term-usage-1"}, {"id": "term-legal-1"}])
    cmd_b = get_test_create_agreement_request_command(requested_terms=[{"id": "term-legal-1"}, {"id": "term-usage-1"}])

    # ACT
    _call_handle(cmd_a, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    _call_handle(cmd_b, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    call_a_kwargs = procurement_service_mock.create_agreement_request.call_args_list[0].kwargs
    call_b_kwargs = procurement_service_mock.create_agreement_request.call_args_list[1].kwargs
    assertpy.assert_that(call_a_kwargs["client_token"]).is_equal_to(call_b_kwargs["client_token"])


def test_derived_client_token_differs_for_a_different_term_set(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """Calibration against over-collapsing: a genuinely different purchase
    must still get its own token, or we would dedupe real distinct buys."""
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd_a = get_test_create_agreement_request_command(requested_terms=[{"id": "term-usage-1"}])
    cmd_b = get_test_create_agreement_request_command(
        requested_terms=[{"id": "term-usage-1", "configuration": {"quantity": 5}}]
    )

    # ACT
    _call_handle(cmd_a, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    _call_handle(cmd_b, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    call_a_kwargs = procurement_service_mock.create_agreement_request.call_args_list[0].kwargs
    call_b_kwargs = procurement_service_mock.create_agreement_request.call_args_list[1].kwargs
    assertpy.assert_that(call_a_kwargs["client_token"]).is_not_equal_to(call_b_kwargs["client_token"])


def test_derived_client_token_differs_per_offer(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """Calibration: two different offers must not share an idempotency key."""
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd_a = get_test_create_agreement_request_command(offer_id="offer-aaaaaaaaaaaa")
    cmd_b = get_test_create_agreement_request_command(offer_id="offer-bbbbbbbbbbbb")

    # ACT
    _call_handle(cmd_a, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    _call_handle(cmd_b, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    # ASSERT
    call_a_kwargs = procurement_service_mock.create_agreement_request.call_args_list[0].kwargs
    call_b_kwargs = procurement_service_mock.create_agreement_request.call_args_list[1].kwargs
    assertpy.assert_that(call_a_kwargs["client_token"]).is_not_equal_to(call_b_kwargs["client_token"])


def test_guard_should_stop_on_first_non_ami_product(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
):
    """When _guard_ami_only encounters a non-AMI product, it must stop
    without calling GetProduct on subsequent products (short-circuit)."""
    # ARRANGE — offer with two products; first is SaaS, second is AMI.
    # Note: the single-product guard would reject this before reaching
    # per-product classification, so we force the guard to reach the loop
    # by supplying exactly one non-AMI product association.
    from app.packaging.domain.read_models.marketplace_offer import MarketplaceOfferProductAssociation

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer(
        associated_products=[MarketplaceOfferProductAssociation(productId="prod-saas-1")]
    )
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details(
        fulfillment_option_types=["SAAS"]
    )
    cmd = get_test_create_agreement_request_command()

    # ACT / ASSERT
    import pytest

    from app.packaging.domain.exceptions.domain_exception import DomainException

    with pytest.raises(DomainException, match="not an AMI product"):
        _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)
    offer_discovery_service_mock.get_product.assert_called_once_with("prod-saas-1")


def test_handle_should_wrap_adapter_exception_from_aws_validation(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
):
    """When AWS's CreateAgreementRequest rejects the payload (e.g.
    ValidationException for a malformed ConfigurableUpfrontPricingTerm
    payload), the adapter raises MarketplaceRequestRejectedException with the AWS message.
    The command handler must re-raise this as a DomainException so the
    middleware surfaces the AWS error to the user as a 400 with a
    meaningful message — not a generic 500 Internal server error that
    hides the real AWS message.
    """
    # ARRANGE
    from app.packaging.domain.exceptions.marketplace_request_rejected_exception import (
        MarketplaceRequestRejectedException,
    )

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.side_effect = MarketplaceRequestRejectedException(
        "Failed to create Marketplace agreement request for proposal at-proposal1: "
        "An error occurred (ValidationException) when calling the "
        "CreateAgreementRequest operation: Provided requested term configuration is invalid."
    )
    cmd = get_test_create_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(DomainException) as excinfo:
        _call_handle(cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock)

    assertpy.assert_that(str(excinfo.value)).contains("AWS Marketplace rejected")
    assertpy.assert_that(str(excinfo.value)).contains(cmd.offerId.value)
    assertpy.assert_that(str(excinfo.value)).contains("Provided requested term configuration is invalid")
    # The DomainException must chain from the original exception so the
    # stack trace preserves the boto3 root cause for CloudWatch debugging.
    assertpy.assert_that(excinfo.value.__cause__).is_instance_of(MarketplaceRequestRejectedException)
    # Event bus must NOT have been called — we don't want to publish an
    # AgreementRequestCreated for a request AWS rejected.
    message_bus_mock.publish.assert_not_called()


# ---------------------------------------------------------------------------
# Duplicate-subscribe guard
#
# AWS Marketplace's ``CreateAgreementRequest`` rejects a second subscription
# to the same (account, offer) with a generic ``ValidationException: This
# action is not supported.`` — the exact same string it uses for
# AWS-managed AMI rejections. We pre-check via ``list_active_agreements``
# and surface a clean, actionable error instead of letting AWS's misleading
# message reach the user.
# ---------------------------------------------------------------------------


def test_handle_should_reject_duplicate_subscribe_to_same_offer(
    offer_discovery_service_mock,
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
):
    """When the account already has an ACTIVE agreement for the same offer,
    reject the request with a friendly domain error — do not call AWS's
    CreateAgreementRequest at all.

    For this case AWS returns "This action is not supported" — the same
    string it uses for AWS-managed AMIs — which is misleading.
    """
    # ARRANGE
    from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    agreement_service_mock.list_active_agreements.return_value = [
        MarketplaceAgreement(
            agreementId="agmt-already-active",
            productId="prod-vew-test-1",
            offerId="offer-abc123",
            status="ACTIVE",
            acceptanceDate="2026-09-10T08:58:08.988+00:00",
        )
    ]
    cmd = get_test_create_agreement_request_command()

    # ACT / ASSERT
    with pytest.raises(DomainException) as excinfo:
        _call_handle(
            cmd,
            offer_discovery_service_mock,
            procurement_service_mock,
            message_bus_mock,
            agreement_mock=agreement_service_mock,
        )
    assertpy.assert_that(str(excinfo.value)).contains("already have an active subscription")
    assertpy.assert_that(str(excinfo.value)).contains("agmt-already-active")
    # Should never have called AWS
    procurement_service_mock.create_agreement_request.assert_not_called()
    message_bus_mock.publish.assert_not_called()


def test_handle_should_allow_subscribe_when_active_agreement_is_for_different_offer(
    offer_discovery_service_mock,
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """The duplicate guard must be per-offer, not per-account. A user with
    an active agreement for offer-A should still be able to subscribe to
    offer-B on the same account.
    """
    # ARRANGE
    from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    agreement_service_mock.list_active_agreements.return_value = [
        MarketplaceAgreement(
            agreementId="agmt-different-offer",
            productId="prod-other",
            offerId="offer-different-from-the-one-we-are-subscribing-to",
            status="ACTIVE",
            acceptanceDate="2026-09-01T00:00:00+00:00",
        )
    ]
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd = get_test_create_agreement_request_command()

    # ACT
    result = _call_handle(
        cmd,
        offer_discovery_service_mock,
        procurement_service_mock,
        message_bus_mock,
        agreement_mock=agreement_service_mock,
    )

    # ASSERT
    assertpy.assert_that(result.agreementRequestId).is_equal_to("ar-1234567890abc")
    procurement_service_mock.create_agreement_request.assert_called_once()


def test_handle_should_degrade_gracefully_when_list_agreements_fails(
    offer_discovery_service_mock,
    procurement_service_mock,
    agreement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """If ``list_active_agreements`` fails (permissions, transient error,
    whatever), the pre-check should be skipped and AWS should have the
    final say. We don't want a bug in our guard to block legitimate
    subscribes.
    """
    # ARRANGE
    from app.packaging.adapters.exceptions.adapter_exception import AdapterException

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    agreement_service_mock.list_active_agreements.side_effect = AdapterException("SearchAgreements permission denied")
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    cmd = get_test_create_agreement_request_command()

    # ACT
    result = _call_handle(
        cmd,
        offer_discovery_service_mock,
        procurement_service_mock,
        message_bus_mock,
        agreement_mock=agreement_service_mock,
    )

    # ASSERT — the call succeeded even though the guard couldn't see the world
    assertpy.assert_that(result.agreementRequestId).is_equal_to("ar-1234567890abc")
    procurement_service_mock.create_agreement_request.assert_called_once()


# ---------------------------------------------------------------------------
# Replay. AWS keys CreateAgreementRequest idempotency on clientToken: the
# same token with the same proposal and terms returns the same
# agreementRequestId. The fake below models that, so a second call that
# reached AWS with a different token would show up as a second request.
# ---------------------------------------------------------------------------


class _IdempotentProcurementFake:
    """Returns one agreement request per distinct clientToken, as AWS does."""

    def __init__(self, quote_factory):
        self._quote_factory = quote_factory
        self.requests_by_token: dict = {}
        self.calls = 0

    def create_agreement_request(self, client_token, agreement_proposal_identifier, requested_terms):
        self.calls += 1
        if client_token not in self.requests_by_token:
            self.requests_by_token[client_token] = self._quote_factory(
                agreement_request_id=f"ar-{len(self.requests_by_token) + 1:012d}"
            )
        return self.requests_by_token[client_token]


@pytest.mark.parametrize("client_token", [None, "3f2b8c1e-9a4d-4e7b-8f60-1c2d3e4f5a6b"])
def test_handle_should_return_the_same_quote_when_called_twice(
    client_token,
    offer_discovery_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """Covers both the caller-supplied token and the derived fallback."""
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_fake = _IdempotentProcurementFake(get_test_agreement_request_quote)
    cmd = get_test_create_agreement_request_command()
    cmd.clientToken = client_token

    # ACT
    first = _call_handle(cmd, offer_discovery_service_mock, procurement_fake, message_bus_mock)
    second = _call_handle(cmd, offer_discovery_service_mock, procurement_fake, message_bus_mock)

    # ASSERT — two calls reached AWS, one agreement request exists
    assertpy.assert_that(procurement_fake.calls).is_equal_to(2)
    assertpy.assert_that(procurement_fake.requests_by_token).is_length(1)
    if client_token:
        assertpy.assert_that(procurement_fake.requests_by_token).contains_key(client_token)
    assertpy.assert_that(second).is_equal_to(first)
    published = [call.args[0] for call in message_bus_mock.publish.call_args_list]
    assertpy.assert_that({e.agreementRequestId for e in published}).is_equal_to({first.agreementRequestId})


def test_handle_should_create_separate_quotes_for_separate_caller_tokens(
    offer_discovery_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    """Calibration: a new wizard attempt sends a new token and must get a
    new quote, even for identical terms."""
    # ARRANGE
    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_fake = _IdempotentProcurementFake(get_test_agreement_request_quote)
    cmd_a = get_test_create_agreement_request_command()
    cmd_a.clientToken = "attempt-1"
    cmd_b = get_test_create_agreement_request_command()
    cmd_b.clientToken = "attempt-2"

    # ACT
    first = _call_handle(cmd_a, offer_discovery_service_mock, procurement_fake, message_bus_mock)
    second = _call_handle(cmd_b, offer_discovery_service_mock, procurement_fake, message_bus_mock)

    # ASSERT
    assertpy.assert_that(second.agreementRequestId).is_not_equal_to(first.agreementRequestId)


# ---------------------------------------------------------------------------
# Publication failure. Once CreateAgreementRequest returns, the agreement
# request exists in AWS; a failure to publish AgreementRequestCreated must
# not hide the quote from the buyer.
# ---------------------------------------------------------------------------


def test_handle_should_return_the_quote_when_publication_fails(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
    caplog,
):
    # ARRANGE
    from unittest import mock

    from app.packaging.domain.command_handlers.marketplace import event_publication
    from app.shared.instrumentation import metrics

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    quote = get_test_agreement_request_quote()
    procurement_service_mock.create_agreement_request.return_value = quote
    message_bus_mock.publish.side_effect = RuntimeError("event bus unavailable")
    metrics_mock = mock.create_autospec(spec=metrics.Metrics)
    cmd = get_test_create_agreement_request_command()

    # ACT
    with caplog.at_level("ERROR", logger="test"):
        result = _call_handle(
            cmd, offer_discovery_service_mock, procurement_service_mock, message_bus_mock, metrics_mock=metrics_mock
        )

    # ASSERT
    assertpy.assert_that(result).is_equal_to(quote)
    metrics_mock.publish_counter.assert_called_once_with(
        metric_name=event_publication.PUBLISH_FAILED_METRIC,
        metric_type=metrics.MetricType.FailedCommand,
    )
    assertpy.assert_that(caplog.text).contains("ar-1234567890abc").contains("event bus unavailable")


def test_handle_should_not_emit_the_failure_metric_on_success(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
    get_test_agreement_request_quote,
):
    # ARRANGE
    from unittest import mock

    from app.shared.instrumentation import metrics

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.return_value = get_test_agreement_request_quote()
    metrics_mock = mock.create_autospec(spec=metrics.Metrics)

    # ACT
    _call_handle(
        get_test_create_agreement_request_command(),
        offer_discovery_service_mock,
        procurement_service_mock,
        message_bus_mock,
        metrics_mock=metrics_mock,
    )

    # ASSERT
    metrics_mock.publish_counter.assert_not_called()


def test_handle_should_not_report_an_aws_outage_as_a_rejected_request(
    offer_discovery_service_mock,
    procurement_service_mock,
    message_bus_mock,
    get_test_create_agreement_request_command,
    get_test_marketplace_offer,
    get_test_ami_product_details,
):
    """Throttling, access denied and outages are not the caller's fault, and their
    message can name the role and the IAM action, so they must not become a 400."""
    from app.packaging.adapters.exceptions.adapter_exception import AdapterException

    offer_discovery_service_mock.get_offer.return_value = get_test_marketplace_offer()
    offer_discovery_service_mock.get_product.return_value = get_test_ami_product_details()
    procurement_service_mock.create_agreement_request.side_effect = AdapterException("AccessDeniedException")

    with pytest.raises(AdapterException):
        _call_handle(
            get_test_create_agreement_request_command(),
            offer_discovery_service_mock,
            procurement_service_mock,
            message_bus_mock,
        )
    message_bus_mock.publish.assert_not_called()
