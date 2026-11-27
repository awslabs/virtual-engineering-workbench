"""Endpoint tests for in-VEW Marketplace procurement.

Covers the endpoints wired up in handler.py. Note the two different scopes:

Project-scoped (browse and quote -- these read catalogue data in the context
of a project):

* GET  /projects/<project_id>/marketplace/purchase-options
* GET  /projects/<project_id>/marketplace/offers/<offer_id>
* POST /projects/<project_id>/marketplace/offers/<offer_id>/quotes

Account-scoped (the agreement itself is an account-level AWS resource with no
project dimension):

* POST   /marketplace/quotes/<agreement_request_id>/accept
* GET    /marketplace/agreements
* DELETE /marketplace/agreements/<agreement_id>
"""

import json
from decimal import Decimal

import assertpy
import pytest

from app.packaging.domain.read_models import agreement_request


def test_list_marketplace_purchase_options_should_return_200(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.packaging.domain.read_models.marketplace_purchase_option import MarketplacePurchaseOption
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_dependencies.marketplace_offer_discovery_svc.list_purchase_options.return_value = [
        MarketplacePurchaseOption(
            purchaseOptionId="po-abc",
            purchaseOptionType="OFFER",
            purchaseOptionName="Standard",
            catalog="AWSMarketplace",
            offerId="offer-abc",
            productId="prod-abc",
            productName="Test AMI Product",
            sellerOfRecordDisplayName="Acme",
        )
    ]

    event = authenticated_event(None, "/projects/proj-123/marketplace/purchase-options", "GET")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    body = json.loads(result["body"])
    assertpy.assert_that(body["purchaseOptions"]).is_length(1)
    assertpy.assert_that(body["purchaseOptions"][0]["offerId"]).is_equal_to("offer-abc")
    assertpy.assert_that(body["purchaseOptions"][0]["purchaseOptionType"]).is_equal_to("OFFER")


def test_get_marketplace_offer_should_return_200_with_terms(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE
    from app.packaging.domain.read_models.marketplace_offer import MarketplaceOffer, MarketplaceOfferProductAssociation
    from app.packaging.domain.read_models.marketplace_offer_term import MarketplaceOfferTerm
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_dependencies.marketplace_offer_discovery_svc.get_offer.return_value = MarketplaceOffer(
        offerId="offer-abc",
        catalog="AWSMarketplace",
        agreementProposalId="at-1",
        sellerOfRecordDisplayName="Acme",
        pricingModelType="UsageBasedPricing",
        associatedProducts=[MarketplaceOfferProductAssociation(productId="prod-1", productName="AMI")],
    )
    mocked_dependencies.marketplace_offer_discovery_svc.get_offer_terms.return_value = [
        MarketplaceOfferTerm(termId="term-legal-1", termType="LegalTerm", rawTerm={"id": "term-legal-1"}),
    ]

    event = authenticated_event(None, "/projects/proj-123/marketplace/offers/offer-abc", "GET")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    body = json.loads(result["body"])
    assertpy.assert_that(body["offerId"]).is_equal_to("offer-abc")
    assertpy.assert_that(body["sellerOfRecordDisplayName"]).is_equal_to("Acme")
    assertpy.assert_that(body["pricingModelType"]).is_equal_to("UsageBasedPricing")
    assertpy.assert_that(body["associatedProducts"]).is_length(1)
    assertpy.assert_that(body["terms"]).is_length(1)


def test_get_marketplace_offer_should_reject_invalid_offer_id(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE — offer id containing a forbidden character (whitespace).
    # The value object does not enforce the legacy "offer-" prefix (AWS
    # Marketplace surfaces both legacy and new 25-char identifiers). It
    # rejects control chars, whitespace inside, and path-traversal
    # attempts as a defense-in-depth check.
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    # NOTE: URL-encode the space so the path routes but the offer_id
    # path param decodes to "offer 123" which contains a real space.
    event = authenticated_event(None, "/projects/proj-123/marketplace/offers/offer%20123", "GET")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT — DomainException raised by the value object surfaces as a 4xx.
    assertpy.assert_that(result["statusCode"]).is_between(400, 499)
    mocked_dependencies.marketplace_offer_discovery_svc.get_offer.assert_not_called()


def test_create_marketplace_quote_should_return_201(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_agreement_request_cmd_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_create_agreement_request_cmd_handler.return_value = agreement_request.AgreementRequestQuote(
        agreementRequestId="ar-1234567890",
        chargeSummary=agreement_request.AgreementChargeSummary(
            newAgreementValue=Decimal("105000.00"),
            newAgreementValueAfterTax=Decimal("119700.00"),
            currencyCode="USD",
        ),
    )

    body = {
        "productType": "AmiProduct",
        "requestedTerms": [{"id": "term-usage-1"}, {"id": "term-legal-1"}],
        "clientToken": "buyer-token-42",
    }
    event = authenticated_event(json.dumps(body), "/projects/proj-123/marketplace/offers/offer-abc/quotes", "POST")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(201)
    payload = json.loads(result["body"])
    assertpy.assert_that(payload["agreementRequestId"]).is_equal_to("ar-1234567890")
    mocked_create_agreement_request_cmd_handler.assert_called_once()


@pytest.mark.parametrize("client_token", ["has space", "under_score", "dot.ted", "ünïcode", ""])
def test_create_marketplace_quote_should_reject_a_client_token_outside_the_aws_charset(
    client_token,
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_agreement_request_cmd_handler,
):
    """AWS accepts only [a-zA-Z0-9-] in ClientToken. Rejecting other
    characters at the API keeps a malformed token from reaching AWS, where
    it would fail only after the offer guards had already run."""
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    body = {"productType": "AmiProduct", "requestedTerms": [{"id": "term-usage-1"}], "clientToken": client_token}
    event = authenticated_event(json.dumps(body), "/projects/proj-123/marketplace/offers/offer-abc/quotes", "POST")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_between(400, 499)
    mocked_create_agreement_request_cmd_handler.assert_not_called()


def test_create_marketplace_quote_should_accept_a_uuid_client_token(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_agreement_request_cmd_handler,
):
    """The frontend sends a UUID per purchase attempt; it must pass."""
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_create_agreement_request_cmd_handler.return_value = agreement_request.AgreementRequestQuote(
        agreementRequestId="ar-1234567890"
    )
    token = "3f2b8c1e-9a4d-4e7b-8f60-1c2d3e4f5a6b"
    body = {"productType": "AmiProduct", "requestedTerms": [{"id": "term-usage-1"}], "clientToken": token}
    event = authenticated_event(json.dumps(body), "/projects/proj-123/marketplace/offers/offer-abc/quotes", "POST")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(201)
    (command,), _ = mocked_create_agreement_request_cmd_handler.call_args
    assertpy.assert_that(command.clientToken).is_equal_to(token)


def test_create_marketplace_quote_should_return_the_estimated_charges(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_agreement_request_cmd_handler,
):
    """A paid CONTRACT total must reach the UI.

    Without these three fields, `formatMoney` in procurement-step-get-quote
    falls through to its "usage-based pricing" fallback for every quote,
    including paid ones.
    """
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_create_agreement_request_cmd_handler.return_value = agreement_request.AgreementRequestQuote(
        agreementRequestId="ar-1234567890",
        chargeSummary=agreement_request.AgreementChargeSummary(
            newAgreementValue=Decimal("105000.00"),
            newAgreementValueAfterTax=Decimal("119700.00"),
            currencyCode="USD",
        ),
    )
    body = {"productType": "AmiProduct", "requestedTerms": [{"id": "term-contract-1"}]}
    event = authenticated_event(json.dumps(body), "/projects/proj-123/marketplace/offers/offer-abc/quotes", "POST")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT — strings, not JSON numbers, so money does not round-trip a float
    payload = json.loads(result["body"])
    assertpy.assert_that(payload["estimatedAgreementValue"]).is_equal_to("105000.00")
    assertpy.assert_that(payload["estimatedAgreementValueAfterTax"]).is_equal_to("119700.00")
    assertpy.assert_that(payload["estimatedCurrencyCode"]).is_equal_to("USD")


def test_create_marketplace_quote_should_null_the_estimates_for_usage_based_pricing(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_create_agreement_request_cmd_handler,
):
    """Calibration: usage-based AMIs legitimately have no up-front total.

    AWS returns no ChargeSummary for them, and the UI is written to render
    "usage-based pricing" on null. Guards against inventing a bogus 0.00.
    """
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_create_agreement_request_cmd_handler.return_value = agreement_request.AgreementRequestQuote(
        agreementRequestId="ar-1234567890",
        chargeSummary=None,
    )
    body = {"productType": "AmiProduct", "requestedTerms": [{"id": "term-usage-1"}]}
    event = authenticated_event(json.dumps(body), "/projects/proj-123/marketplace/offers/offer-abc/quotes", "POST")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    payload = json.loads(result["body"])
    assertpy.assert_that(payload["agreementRequestId"]).is_equal_to("ar-1234567890")
    assertpy.assert_that(payload["estimatedAgreementValue"]).is_none()
    assertpy.assert_that(payload["estimatedAgreementValueAfterTax"]).is_none()
    assertpy.assert_that(payload["estimatedCurrencyCode"]).is_none()


def test_accept_marketplace_quote_should_return_200(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_accept_agreement_request_cmd_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_accept_agreement_request_cmd_handler.return_value = "agmt-abc123"

    event = authenticated_event(None, "/marketplace/quotes/ar-1234567890/accept", "POST")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    payload = json.loads(result["body"])
    assertpy.assert_that(payload["agreementId"]).is_equal_to("agmt-abc123")


def test_cancel_marketplace_agreement_should_return_200(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_cancel_agreement_cmd_handler,
):
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    event = authenticated_event(None, "/marketplace/agreements/agmt-abc123", "DELETE")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    payload = json.loads(result["body"])
    assertpy.assert_that(payload["agreementId"]).is_equal_to("agmt-abc123")
    mocked_cancel_agreement_cmd_handler.assert_called_once()


def test_list_marketplace_agreements_should_return_200(lambda_context, authenticated_event, mocked_dependencies):
    """GET /marketplace/agreements returns the buyer's active agreements
    (AMI-only). Reuses the discovery adapter; the AMI-only
    filter runs inside the adapter, after SearchAgreements.

    Each row is enriched with ``productName`` / ``offerName`` /
    ``pricingModelType`` via one ``GetOffer`` call per agreement.
    """
    # ARRANGE
    from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement
    from app.packaging.domain.read_models.marketplace_offer import MarketplaceOffer, MarketplaceOfferProductAssociation
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_dependencies.marketplace_discovery_svc.list_active_agreements.return_value = [
        MarketplaceAgreement(
            agreementId="agmt-abc123",
            productId="prod-xyz",
            offerId="offer-abc",
            status="ACTIVE",
            acceptanceDate="2026-09-01T00:00:00Z",
        )
    ]
    mocked_dependencies.marketplace_offer_discovery_svc.get_offer.return_value = MarketplaceOffer(
        offerId="offer-abc",
        catalog="AWSMarketplace",
        offerName="Ubuntu Noble standard offer",
        agreementProposalId="ap-abc",
        pricingModelType="FREE",
        associatedProducts=[
            MarketplaceOfferProductAssociation(
                productId="prod-xyz",
                productName="Ubuntu 24.04 LTS - Noble",
            )
        ],
    )

    event = authenticated_event(None, "/marketplace/agreements", "GET")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    body = json.loads(result["body"])
    assertpy.assert_that(body["agreements"]).is_length(1)
    row = body["agreements"][0]
    assertpy.assert_that(row["agreementId"]).is_equal_to("agmt-abc123")
    assertpy.assert_that(row["productId"]).is_equal_to("prod-xyz")
    assertpy.assert_that(row["status"]).is_equal_to("ACTIVE")
    # Enrichment fields
    assertpy.assert_that(row["productName"]).is_equal_to("Ubuntu 24.04 LTS - Noble")
    assertpy.assert_that(row["offerName"]).is_equal_to("Ubuntu Noble standard offer")
    assertpy.assert_that(row["pricingModelType"]).is_equal_to("FREE")
    mocked_dependencies.marketplace_discovery_svc.list_active_agreements.assert_called_once()
    mocked_dependencies.marketplace_offer_discovery_svc.get_offer.assert_called_once_with("offer-abc")


def test_list_marketplace_agreements_should_fall_back_on_enrichment_failure(
    lambda_context, authenticated_event, mocked_dependencies
):
    """If ``GetOffer`` fails for a specific agreement (rate limit,
    permission drift, product delisted), the row still appears in the
    response with ``None`` enrichment fields — the UI should fall back
    to showing raw IDs. A single bad row must not fail the whole list.
    """
    # ARRANGE
    from app.packaging.adapters.exceptions.adapter_exception import AdapterException
    from app.packaging.domain.read_models.marketplace_agreement import MarketplaceAgreement
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_dependencies.marketplace_discovery_svc.list_active_agreements.return_value = [
        MarketplaceAgreement(
            agreementId="agmt-abc123",
            productId="prod-xyz",
            offerId="offer-abc",
            status="ACTIVE",
            acceptanceDate="2026-09-01T00:00:00Z",
        )
    ]
    mocked_dependencies.marketplace_offer_discovery_svc.get_offer.side_effect = AdapterException(
        "GetOffer failed: rate limit exceeded"
    )

    event = authenticated_event(None, "/marketplace/agreements", "GET")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT — row is present, raw IDs preserved, enrichment fields None
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    body = json.loads(result["body"])
    assertpy.assert_that(body["agreements"]).is_length(1)
    row = body["agreements"][0]
    assertpy.assert_that(row["agreementId"]).is_equal_to("agmt-abc123")
    assertpy.assert_that(row["productId"]).is_equal_to("prod-xyz")
    assertpy.assert_that(row["offerId"]).is_equal_to("offer-abc")
    assertpy.assert_that(row["productName"]).is_none()
    assertpy.assert_that(row["offerName"]).is_none()
    assertpy.assert_that(row["pricingModelType"]).is_none()


def test_list_marketplace_agreements_should_return_empty_list(lambda_context, authenticated_event, mocked_dependencies):
    # ARRANGE — adapter returns empty (no agreements or access denied → graceful).
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_dependencies.marketplace_discovery_svc.list_active_agreements.return_value = []

    event = authenticated_event(None, "/marketplace/agreements", "GET")

    # ACT
    result = handler.handler(event, lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    body = json.loads(result["body"])
    assertpy.assert_that(body["agreements"]).is_length(0)


def test_project_scoped_agreement_routes_return_404(lambda_context, authenticated_event, mocked_dependencies):
    """Project-scoped agreement routes must not resolve.

    Agreements are account-level resources with no project dimension. A
    project in the URL would claim a scope nothing enforces: an admin of
    project A, correctly authorized for project A by AVP, could list and
    cancel subscriptions that project B relies on. These paths must 404.
    """
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    for path, method in [
        ("/projects/proj-123/marketplace/agreements", "GET"),
        ("/projects/proj-123/marketplace/agreements/agmt-abc123", "DELETE"),
        ("/projects/proj-123/marketplace/quotes/ar-1234567890/accept", "POST"),
    ]:
        # ACT
        result = handler.handler(authenticated_event(None, path, method), lambda_context)

        # ASSERT
        assertpy.assert_that(result["statusCode"]).described_as(f"{method} {path}").is_equal_to(404)

    mocked_dependencies.marketplace_discovery_svc.list_active_agreements.assert_not_called()


def test_cancel_agreement_command_carries_no_project(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_cancel_agreement_cmd_handler,
):
    """The cancel command must not carry a projectId.

    An agreement has no project to validate it against, so the field would
    be a scope claim with no enforcement behind it. A field that looks like
    an authorization boundary but is never checked is worse than no field,
    because readers assume it is checked.
    """
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies

    # ACT
    result = handler.handler(authenticated_event(None, "/marketplace/agreements/agmt-abc123", "DELETE"), lambda_context)

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    (command,), _ = mocked_cancel_agreement_cmd_handler.call_args
    assertpy.assert_that(hasattr(command, "projectId")).is_false()
    assertpy.assert_that(command.agreementId.value).is_equal_to("agmt-abc123")


def test_accept_quote_command_carries_no_project(
    lambda_context,
    authenticated_event,
    mocked_dependencies,
    mocked_accept_agreement_request_cmd_handler,
):
    """Same as the cancel case: accepting a quote commits the buyer ACCOUNT."""
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_accept_agreement_request_cmd_handler.return_value = "agmt-abc123"

    # ACT
    result = handler.handler(
        authenticated_event(None, "/marketplace/quotes/ar-1234567890/accept", "POST"), lambda_context
    )

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
    (command,), _ = mocked_accept_agreement_request_cmd_handler.call_args
    assertpy.assert_that(hasattr(command, "projectId")).is_false()
    assertpy.assert_that(command.agreementRequestId.value).is_equal_to("ar-1234567890")


def test_project_scoped_browse_routes_resolve(lambda_context, authenticated_event, mocked_dependencies):
    """Calibration: the browse/quote routes are project-scoped.

    Without this, the 404 assertions above could pass simply because the whole
    Marketplace surface had been removed or broken.
    """
    # ARRANGE
    from app.packaging.entrypoints.api import handler

    handler.dependencies = mocked_dependencies
    mocked_dependencies.marketplace_offer_discovery_svc.list_purchase_options.return_value = []

    # ACT
    result = handler.handler(
        authenticated_event(None, "/projects/proj-123/marketplace/purchase-options", "GET"), lambda_context
    )

    # ASSERT
    assertpy.assert_that(result["statusCode"]).is_equal_to(200)
