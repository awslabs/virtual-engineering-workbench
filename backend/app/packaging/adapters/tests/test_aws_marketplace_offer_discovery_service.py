import assertpy
import pytest
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.adapters.tests.conftest import GlobalVariables


def test_should_list_purchase_options(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ACT
    result = get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT
    mock_moto_calls["ListPurchaseOptions"].assert_called_once()
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].offerId).is_equal_to(GlobalVariables.TEST_MARKETPLACE_OFFER_ID.value)
    assertpy.assert_that(result[0].productId).is_equal_to(GlobalVariables.TEST_MARKETPLACE_PRODUCT_ID.value)
    assertpy.assert_that(result[0].purchaseOptionType).is_equal_to("OFFER")
    assertpy.assert_that(result[0].partOfOfferSet).is_false()


def test_should_send_visibility_scope_filter_to_list_purchase_options(
    mock_moto_calls, get_marketplace_offer_discovery_srv
):
    """AWS's ListPurchaseOptions requires at least one filter and exposes no
    product-type filter: its filterType enum is PRODUCT_ID /
    SELLER_OF_RECORD_PROFILE_ID / PURCHASE_OPTION_TYPE / VISIBILITY_SCOPE /
    AVAILABILITY_STATUS. The only VISIBILITY_SCOPE value AWS accepts is
    PRIVATE (PUBLIC / SHARED are rejected with ValidationException).

    VISIBILITY_SCOPE limits visibility, not product type, so it contributes
    nothing to the AMI-only invariant -- which the adapter therefore enforces
    itself by resolving each product through GetProduct."""
    # ACT
    get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT
    _, called_kwargs = mock_moto_calls["ListPurchaseOptions"].call_args
    filters = called_kwargs.get("filters", [])
    assertpy.assert_that(filters).is_length(1)
    assertpy.assert_that(filters[0]).is_equal_to({"filterType": "VISIBILITY_SCOPE", "filterValues": ["PRIVATE"]})


def test_should_paginate_list_purchase_options(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ARRANGE — first page has nextToken, second page has none.
    def _summary(purchase_option_id: str, product_id: str, offer_id: str):
        return {
            "purchaseOptionId": purchase_option_id,
            "catalog": "AWSMarketplace",
            "purchaseOptionType": "OFFER",
            "sellerOfRecord": {"sellerProfileId": "s-1", "displayName": "Acme"},
            "associatedEntities": [
                {
                    "product": {"productId": product_id, "productName": "AMI"},
                    "offer": {"offerId": offer_id, "sellerOfRecord": {"sellerProfileId": "s-1"}},
                }
            ],
        }

    first_page = {"purchaseOptions": [_summary("po-1", "prod-1", "offer-1")], "nextToken": "token-page-2"}
    second_page = {"purchaseOptions": [_summary("po-2", "prod-2", "offer-2")]}
    mock_moto_calls["ListPurchaseOptions"].side_effect = [first_page, second_page]

    # ACT
    result = get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT
    assertpy.assert_that(mock_moto_calls["ListPurchaseOptions"].call_count).is_equal_to(2)
    assertpy.assert_that(result).is_length(2)
    assertpy.assert_that([r.offerId for r in result]).is_equal_to(["offer-1", "offer-2"])


def test_should_surface_offer_set_membership_on_purchase_option(mock_moto_calls, get_marketplace_offer_discovery_srv):
    """OFFERSET purchase options carry more than one product/offer pair
    and must be surfaced with partOfOfferSet=True so the buyer UI can
    render bundle info and the domain guard can reject bundles at the
    purchase-time step."""
    # ARRANGE
    mock_moto_calls["ListPurchaseOptions"].return_value = {
        "purchaseOptions": [
            {
                "purchaseOptionId": "po-bundle-1",
                "catalog": "AWSMarketplace",
                "purchaseOptionType": "OFFERSET",
                "sellerOfRecord": {"sellerProfileId": "s-1", "displayName": "Acme"},
                "associatedEntities": [
                    {
                        "product": {"productId": "prod-a", "productName": "AMI-A"},
                        "offer": {"offerId": "offer-a", "sellerOfRecord": {"sellerProfileId": "s-1"}},
                        "offerSet": {"offerSetId": "offset-1", "sellerOfRecord": {"sellerProfileId": "s-1"}},
                    },
                    {
                        "product": {"productId": "prod-b", "productName": "AMI-B"},
                        "offer": {"offerId": "offer-b", "sellerOfRecord": {"sellerProfileId": "s-1"}},
                        "offerSet": {"offerSetId": "offset-1", "sellerOfRecord": {"sellerProfileId": "s-1"}},
                    },
                ],
            }
        ]
    }

    # ACT
    result = get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT
    assertpy.assert_that(result).is_length(2)
    assertpy.assert_that([r.offerId for r in result]).is_equal_to(["offer-a", "offer-b"])
    for entry in result:
        assertpy.assert_that(entry.partOfOfferSet).is_true()
        assertpy.assert_that(entry.purchaseOptionType).is_equal_to("OFFERSET")


def test_should_raise_adapter_exception_when_list_purchase_options_fails(
    mock_moto_calls, get_marketplace_offer_discovery_srv
):
    # ARRANGE
    mock_moto_calls["ListPurchaseOptions"].side_effect = ClientError(
        error_response={"Error": {"Code": "InternalServerException", "Message": "boom"}},
        operation_name="ListPurchaseOptions",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_offer_discovery_srv.list_purchase_options()


def test_should_get_offer_and_flatten_seller_and_pricing_structs(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ACT
    offer = get_marketplace_offer_discovery_srv.get_offer(GlobalVariables.TEST_MARKETPLACE_OFFER_ID.value)

    # ASSERT — the AWS response nests sellerOfRecord and pricingModel as
    # structs; the adapter flattens them into scalar fields to keep the
    # read model dict-free.
    mock_moto_calls["GetOffer"].assert_called_once_with(offerId=GlobalVariables.TEST_MARKETPLACE_OFFER_ID.value)
    assertpy.assert_that(offer.offerId).is_equal_to(GlobalVariables.TEST_MARKETPLACE_OFFER_ID.value)
    assertpy.assert_that(offer.agreementProposalId).is_equal_to("at-proposalabc123")
    assertpy.assert_that(offer.catalog).is_equal_to("AWSMarketplace")
    assertpy.assert_that(offer.sellerOfRecordDisplayName).is_equal_to(GlobalVariables.TEST_MARKETPLACE_PUBLISHER.value)
    assertpy.assert_that(offer.sellerOfRecordProfileId).is_equal_to("seller-1")
    assertpy.assert_that(offer.pricingModelType).is_equal_to("UsageBasedPricing")
    assertpy.assert_that(offer.pricingModelDisplayName).is_equal_to("Usage-based pricing")
    assertpy.assert_that(offer.associatedProducts).is_length(1)
    assertpy.assert_that(offer.associatedProducts[0].productId).is_equal_to(
        GlobalVariables.TEST_MARKETPLACE_PRODUCT_ID.value
    )
    assertpy.assert_that(offer.associatedProducts[0].partOfOfferSet).is_false()


def test_should_surface_offer_set_membership_on_get_offer(mock_moto_calls, get_marketplace_offer_discovery_srv):
    """When the fetched offer is part of a bundle, associatedEntities[]
    carries an offerSet grouping; the domain guard needs to see the flag
    rather than have it swallowed by the adapter."""
    # ARRANGE
    mock_moto_calls["GetOffer"].return_value = {
        "offerId": "offer-bundle-1",
        "catalog": "AWSMarketplace",
        "agreementProposalId": "at-bundle-1",
        "sellerOfRecord": {"sellerProfileId": "s-1", "displayName": "Acme"},
        "associatedEntities": [
            {
                "product": {"productId": "prod-1", "productName": "AMI"},
                "offerSet": {"offerSetId": "offset-1", "sellerOfRecord": {"sellerProfileId": "s-1"}},
            },
        ],
    }

    # ACT
    offer = get_marketplace_offer_discovery_srv.get_offer("offer-bundle-1")

    # ASSERT
    assertpy.assert_that(offer.associatedProducts).is_length(1)
    assertpy.assert_that(offer.associatedProducts[0].partOfOfferSet).is_true()


def test_should_get_product_and_project_ami_fulfillment_type(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ACT
    product = get_marketplace_offer_discovery_srv.get_product(GlobalVariables.TEST_MARKETPLACE_PRODUCT_ID.value)

    # ASSERT
    mock_moto_calls["GetProduct"].assert_called_once_with(productId=GlobalVariables.TEST_MARKETPLACE_PRODUCT_ID.value)
    assertpy.assert_that(product.productId).is_equal_to(GlobalVariables.TEST_MARKETPLACE_PRODUCT_ID.value)
    assertpy.assert_that(product.fulfillmentOptionTypes).is_equal_to(["AMAZON_MACHINE_IMAGE"])
    assertpy.assert_that(product.is_ami_product()).is_true()


def test_get_product_should_classify_non_ami_product_correctly(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ARRANGE — SaaS product classification.
    mock_moto_calls["GetProduct"].return_value = {
        "productId": "prod-saas-1",
        "catalog": "AWSMarketplace",
        "productName": "SaaS Thing",
        "manufacturer": {"sellerProfileId": "s-1", "displayName": "Acme"},
        "fulfillmentOptionSummaries": [{"fulfillmentOptionType": "SAAS"}],
    }

    # ACT
    product = get_marketplace_offer_discovery_srv.get_product("prod-saas-1")

    # ASSERT
    assertpy.assert_that(product.is_ami_product()).is_false()


def test_should_raise_adapter_exception_when_get_product_fails(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ARRANGE
    mock_moto_calls["GetProduct"].side_effect = ClientError(
        error_response={"Error": {"Code": "ResourceNotFoundException", "Message": "no product"}},
        operation_name="GetProduct",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_offer_discovery_srv.get_product("prod-missing")


def test_should_reject_an_unknown_offer_as_a_caller_error(mock_moto_calls, get_marketplace_offer_discovery_srv):
    from app.packaging.domain.exceptions.marketplace_request_rejected_exception import (
        MarketplaceRequestRejectedException,
    )

    # ARRANGE
    mock_moto_calls["GetOffer"].side_effect = ClientError(
        error_response={"Error": {"Code": "ResourceNotFoundException", "Message": "no such offer"}},
        operation_name="GetOffer",
    )

    # ACT / ASSERT
    with pytest.raises(MarketplaceRequestRejectedException):
        get_marketplace_offer_discovery_srv.get_offer("offer-does-not-exist")


def test_should_raise_adapter_exception_when_get_offer_is_throttled(
    mock_moto_calls, get_marketplace_offer_discovery_srv
):
    # ARRANGE
    mock_moto_calls["GetOffer"].side_effect = ClientError(
        error_response={"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
        operation_name="GetOffer",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_offer_discovery_srv.get_offer("offer-abc123")


def test_should_get_offer_terms_and_flatten_wrapper_dict(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ACT
    terms = get_marketplace_offer_discovery_srv.get_offer_terms(GlobalVariables.TEST_MARKETPLACE_OFFER_ID.value)

    # ASSERT — AWS wraps each term in a single-key dict where the outer key
    # is a camelCase alias and the inner payload has both id and a
    # PascalCase type discriminator. We surface the inner ``type`` field,
    # not the outer key, because Agreements API term configurations
    # reference the PascalCase type.
    mock_moto_calls["GetOfferTerms"].assert_called_once_with(offerId=GlobalVariables.TEST_MARKETPLACE_OFFER_ID.value)
    assertpy.assert_that(terms).is_length(2)
    assertpy.assert_that([t.termType for t in terms]).is_equal_to(["LegalTerm", "UsageBasedPricingTerm"])
    assertpy.assert_that([t.termId for t in terms]).is_equal_to(["term-legal-1", "term-usage-1"])
    # rawTerm should retain the full inner payload for callers that need
    # to build configurable-term configurations.
    assertpy.assert_that(terms[1].rawTerm).contains_key("rateCards")


def test_should_paginate_get_offer_terms(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ARRANGE
    first_page = {
        "offerTerms": [{"legalTerm": {"id": "term-legal-1", "type": "LegalTerm"}}],
        "nextToken": "token-page-2",
    }
    second_page = {"offerTerms": [{"usageBasedPricingTerm": {"id": "term-usage-1", "type": "UsageBasedPricingTerm"}}]}
    mock_moto_calls["GetOfferTerms"].side_effect = [first_page, second_page]

    # ACT
    terms = get_marketplace_offer_discovery_srv.get_offer_terms("offer-x")

    # ASSERT
    assertpy.assert_that(mock_moto_calls["GetOfferTerms"].call_count).is_equal_to(2)
    assertpy.assert_that([t.termId for t in terms]).is_equal_to(["term-legal-1", "term-usage-1"])


def test_should_return_empty_terms_when_offer_has_none(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ARRANGE
    mock_moto_calls["GetOfferTerms"].return_value = {"offerTerms": []}

    # ACT
    terms = get_marketplace_offer_discovery_srv.get_offer_terms("offer-empty")

    # ASSERT
    assertpy.assert_that(terms).is_empty()


def test_should_skip_malformed_offer_terms(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ARRANGE — mixed valid and malformed entries.
    mock_moto_calls["GetOfferTerms"].return_value = {
        "offerTerms": [
            {},  # empty wrapper
            {"legalTerm": "not-a-dict"},  # payload is not a dict
            {"supportTerm": {"id": "term-support-1", "type": "SupportTerm"}},
        ]
    }

    # ACT
    terms = get_marketplace_offer_discovery_srv.get_offer_terms("offer-x")

    # ASSERT
    assertpy.assert_that(terms).is_length(1)
    assertpy.assert_that(terms[0].termId).is_equal_to("term-support-1")
    assertpy.assert_that(terms[0].termType).is_equal_to("SupportTerm")


def test_should_raise_adapter_exception_when_get_offer_terms_fails(
    mock_moto_calls, get_marketplace_offer_discovery_srv
):
    # ARRANGE
    mock_moto_calls["GetOfferTerms"].side_effect = ClientError(
        error_response={"Error": {"Code": "ValidationException", "Message": "bad id"}},
        operation_name="GetOfferTerms",
    )

    # ACT / ASSERT
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_offer_discovery_srv.get_offer_terms("offer-bad")


# ---------------------------------------------------------------------------
# VISIBILITY_SCOPE limits visibility, not product type, so without its own
# check the adapter would return Container / SaaS / other private offers
# through a port whose contract says AMI-only, and the buyer UI would present
# them as AMIs that the purchase guard then refuses.
# ---------------------------------------------------------------------------
def _po_summary(purchase_option_id: str, product_id: str, offer_id: str):
    return {
        "purchaseOptionId": purchase_option_id,
        "catalog": "AWSMarketplace",
        "purchaseOptionType": "OFFER",
        "sellerOfRecord": {"sellerProfileId": "s-1", "displayName": "Acme"},
        "associatedEntities": [
            {
                "product": {"productId": product_id, "productName": product_id},
                "offer": {"offerId": offer_id, "sellerOfRecord": {"sellerProfileId": "s-1"}},
            }
        ],
    }


def _product(product_id: str, fulfillment_type: str):
    return {
        "productId": product_id,
        "catalog": "AWSMarketplace",
        "productName": product_id,
        "manufacturer": {"sellerProfileId": "s-1", "displayName": "Acme"},
        "fulfillmentOptionSummaries": [{"fulfillmentOptionType": fulfillment_type}],
    }


def test_list_purchase_options_should_exclude_non_ami_products(mock_moto_calls, get_marketplace_offer_discovery_srv):
    # ARRANGE — one AMI, one Container, one SaaS private offer.
    mock_moto_calls["ListPurchaseOptions"].return_value = {
        "purchaseOptions": [
            _po_summary("po-ami", "prod-ami", "offer-ami"),
            _po_summary("po-container", "prod-container", "offer-container"),
            _po_summary("po-saas", "prod-saas", "offer-saas"),
        ]
    }
    products = {
        "prod-ami": _product("prod-ami", "AMAZON_MACHINE_IMAGE"),
        "prod-container": _product("prod-container", "CONTAINER"),
        "prod-saas": _product("prod-saas", "SAAS"),
    }
    mock_moto_calls["GetProduct"].side_effect = lambda productId: products[productId]

    # ACT
    result = get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT — only the AMI option survives.
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].productId).is_equal_to("prod-ami")


def test_list_purchase_options_should_keep_a_product_with_an_ami_among_several_fulfillments(
    mock_moto_calls, get_marketplace_offer_discovery_srv
):
    """A product offering both a Container and an AMI is still an AMI product.

    Calibration against over-filtering: the exclusion must key off "has no AMI
    fulfillment option", not "has a non-AMI one".
    """
    # ARRANGE
    mock_moto_calls["ListPurchaseOptions"].return_value = {
        "purchaseOptions": [_po_summary("po-multi", "prod-multi", "offer-multi")]
    }
    mock_moto_calls["GetProduct"].return_value = {
        "productId": "prod-multi",
        "catalog": "AWSMarketplace",
        "productName": "Multi",
        "manufacturer": {"sellerProfileId": "s-1", "displayName": "Acme"},
        "fulfillmentOptionSummaries": [
            {"fulfillmentOptionType": "CONTAINER"},
            {"fulfillmentOptionType": "AMAZON_MACHINE_IMAGE"},
        ],
    }

    # ACT
    result = get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT
    assertpy.assert_that(result).is_length(1)


def test_list_purchase_options_should_exclude_a_product_it_cannot_resolve(
    mock_moto_calls, get_marketplace_offer_discovery_srv
):
    """An unresolvable product is omitted, not included optimistically.

    The port promises AMI products. On an ambiguous answer, omitting the row
    is honest; presenting an unverified product to the buyer as an AMI is not.
    """
    # ARRANGE
    mock_moto_calls["ListPurchaseOptions"].return_value = {
        "purchaseOptions": [
            _po_summary("po-ami", "prod-ami", "offer-ami"),
            _po_summary("po-denied", "prod-denied", "offer-denied"),
        ]
    }

    def _get_product(productId: str):
        if productId == "prod-denied":
            raise ClientError(
                error_response={"Error": {"Code": "AccessDeniedException", "Message": "denied"}},
                operation_name="GetProduct",
            )
        return _product(productId, "AMAZON_MACHINE_IMAGE")

    mock_moto_calls["GetProduct"].side_effect = _get_product

    # ACT
    result = get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT
    assertpy.assert_that(result).is_length(1)
    assertpy.assert_that(result[0].productId).is_equal_to("prod-ami")


def test_list_purchase_options_should_resolve_each_product_once(mock_moto_calls, get_marketplace_offer_discovery_srv):
    """Several offers for the same product cost one GetProduct call.

    Without memoisation the AMI check adds one AWS call per offer, so a
    catalogue with many offers on one product would multiply the request
    count for no new information.
    """
    # ARRANGE — three distinct offers, all on the same product.
    mock_moto_calls["ListPurchaseOptions"].return_value = {
        "purchaseOptions": [
            _po_summary("po-1", "prod-same", "offer-1"),
            _po_summary("po-2", "prod-same", "offer-2"),
            _po_summary("po-3", "prod-same", "offer-3"),
        ]
    }
    mock_moto_calls["GetProduct"].return_value = _product("prod-same", "AMAZON_MACHINE_IMAGE")

    # ACT
    result = get_marketplace_offer_discovery_srv.list_purchase_options()

    # ASSERT
    assertpy.assert_that(result).is_length(3)
    assertpy.assert_that(mock_moto_calls["GetProduct"].call_count).is_equal_to(1)
