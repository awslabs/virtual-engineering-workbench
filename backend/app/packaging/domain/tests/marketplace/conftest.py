"""Fixtures for the packaging domain marketplace command handler tests."""

from unittest import mock

import pytest

from app.packaging.domain.commands.marketplace import (
    accept_agreement_request_command,
    cancel_agreement_command,
    create_agreement_request_command,
)
from app.packaging.domain.ports.marketplace_agreement_service import MarketplaceAgreementService
from app.packaging.domain.ports.marketplace_offer_discovery_service import MarketplaceOfferDiscoveryService
from app.packaging.domain.ports.marketplace_procurement_service import MarketplaceProcurementService
from app.packaging.domain.read_models.agreement_request import (
    AcceptedAgreement,
    AgreementChargeSummary,
    AgreementRequestQuote,
)
from app.packaging.domain.read_models.marketplace_offer import MarketplaceOffer, MarketplaceOfferProductAssociation
from app.packaging.domain.read_models.marketplace_product_details import MarketplaceProductDetails
from app.packaging.domain.value_objects.marketplace import (
    agreement_id_value_object,
    agreement_request_id_value_object,
    offer_id_value_object,
)
from app.packaging.domain.value_objects.shared import project_id_value_object

TEST_PROJECT_ID = "proj-12345"
TEST_OFFER_ID = "offer-abc123"
TEST_PRODUCT_ID = "prod-vew-test-1"
TEST_AGREEMENT_PROPOSAL_ID = "at-proposal1"
TEST_AGREEMENT_REQUEST_ID = "ar-1234567890abc"
TEST_AGREEMENT_ID = "agmt-1234567890abc"


@pytest.fixture()
def offer_discovery_service_mock():
    return mock.create_autospec(spec=MarketplaceOfferDiscoveryService)


@pytest.fixture()
def procurement_service_mock():
    return mock.create_autospec(spec=MarketplaceProcurementService)


@pytest.fixture()
def agreement_service_mock():
    """Default: no active agreements — the duplicate-subscribe guard is
    a no-op, so existing tests exercising the happy path stay valid.
    Individual tests override ``list_active_agreements.return_value``
    when they need to test the duplicate case explicitly.
    """
    m = mock.create_autospec(spec=MarketplaceAgreementService)
    m.list_active_agreements.return_value = []
    return m


@pytest.fixture()
def get_test_marketplace_offer():
    def _factory(
        offer_id: str = TEST_OFFER_ID,
        agreement_proposal_id: str = TEST_AGREEMENT_PROPOSAL_ID,
        associated_products: list[MarketplaceOfferProductAssociation] | None = None,
    ) -> MarketplaceOffer:
        return MarketplaceOffer(
            offerId=offer_id,
            catalog="AWSMarketplace",
            offerName="Test Offer",
            agreementProposalId=agreement_proposal_id,
            associatedProducts=(
                associated_products
                if associated_products is not None
                else [MarketplaceOfferProductAssociation(productId=TEST_PRODUCT_ID, productName="AMI Product")]
            ),
        )

    return _factory


@pytest.fixture()
def get_test_ami_product_details():
    def _factory(
        product_id: str = TEST_PRODUCT_ID,
        fulfillment_option_types: list[str] | None = None,
    ) -> MarketplaceProductDetails:
        return MarketplaceProductDetails(
            productId=product_id,
            productName="AMI Product",
            fulfillmentOptionTypes=(
                fulfillment_option_types if fulfillment_option_types is not None else ["AMAZON_MACHINE_IMAGE"]
            ),
        )

    return _factory


@pytest.fixture()
def get_test_create_agreement_request_command():
    def _factory(
        offer_id: str = TEST_OFFER_ID,
        requested_terms: list[dict] | None = None,
    ):
        return create_agreement_request_command.CreateAgreementRequestCommand(
            projectId=project_id_value_object.from_str(TEST_PROJECT_ID),
            offerId=offer_id_value_object.from_str(offer_id),
            requestedTerms=(
                requested_terms if requested_terms is not None else [{"id": "term-usage-1"}, {"id": "term-legal-1"}]
            ),
        )

    return _factory


@pytest.fixture()
def get_test_accept_agreement_request_command():
    def _factory(agreement_request_id: str = TEST_AGREEMENT_REQUEST_ID):
        return accept_agreement_request_command.AcceptAgreementRequestCommand(
            agreementRequestId=agreement_request_id_value_object.from_str(agreement_request_id),
        )

    return _factory


@pytest.fixture()
def get_test_cancel_agreement_command():
    def _factory(agreement_id: str = TEST_AGREEMENT_ID):
        return cancel_agreement_command.CancelAgreementCommand(
            agreementId=agreement_id_value_object.from_str(agreement_id),
        )

    return _factory


@pytest.fixture()
def get_test_agreement_request_quote():
    def _factory(
        agreement_request_id: str = TEST_AGREEMENT_REQUEST_ID,
        new_agreement_value: str | None = "42.00",
        new_agreement_value_after_tax: str | None = "46.20",
        currency: str | None = "USD",
    ) -> AgreementRequestQuote:
        summary = None
        if new_agreement_value is not None or currency is not None:
            from decimal import Decimal

            summary = AgreementChargeSummary(
                newAgreementValue=Decimal(new_agreement_value) if new_agreement_value else None,
                newAgreementValueAfterTax=(
                    Decimal(new_agreement_value_after_tax) if new_agreement_value_after_tax else None
                ),
                currencyCode=currency,
            )
        return AgreementRequestQuote(agreementRequestId=agreement_request_id, chargeSummary=summary)

    return _factory


@pytest.fixture()
def get_test_accepted_agreement():
    def _factory(agreement_id: str = TEST_AGREEMENT_ID) -> AcceptedAgreement:
        return AcceptedAgreement(agreementId=agreement_id)

    return _factory
