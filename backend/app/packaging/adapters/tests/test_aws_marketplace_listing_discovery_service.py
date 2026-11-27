import assertpy
import pytest
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception


def test_should_search_listings_returns_listings(mock_moto_calls, get_marketplace_listing_discovery_srv):
    result = get_marketplace_listing_discovery_srv.search_listings()

    mock_moto_calls["SearchListings"].assert_called_once()
    assertpy.assert_that(result.listings).is_length(1)
    assertpy.assert_that(result.totalResults).is_equal_to(7385)
    assertpy.assert_that(result.nextToken).is_equal_to("opaque-next-token")

    listing = result.listings[0]
    assertpy.assert_that(listing.listingId).is_equal_to("prodview-testlisting01")
    assertpy.assert_that(listing.listingName).is_equal_to("Test AMI Listing")
    assertpy.assert_that(listing.publisher.displayName).is_equal_to("Test Seller Inc.")
    assertpy.assert_that(listing.primaryProductId).is_equal_to("prod-test01")
    assertpy.assert_that(listing.primaryOfferId).is_equal_to("offer-test01")
    assertpy.assert_that(len(listing.reviewSummary)).is_equal_to(1)
    assertpy.assert_that(listing.reviewSummary[0].averageRating).is_equal_to("4.5")


def test_search_listings_locks_ami_and_single_product_filters(mock_moto_calls, get_marketplace_listing_discovery_srv):
    """Server-side invariant: FULFILLMENT_OPTION_TYPE=AMAZON_MACHINE_IMAGE
    and NUMBER_OF_PRODUCTS=SINGLE_PRODUCT are always applied and cannot
    be overridden by callers."""
    get_marketplace_listing_discovery_srv.search_listings()
    _, kwargs = mock_moto_calls["SearchListings"].call_args
    filters = kwargs.get("filters", [])
    filter_types = {(f["filterType"], tuple(f["filterValues"])) for f in filters}
    assertpy.assert_that(filter_types).contains(("FULFILLMENT_OPTION_TYPE", ("AMAZON_MACHINE_IMAGE",)))
    assertpy.assert_that(filter_types).contains(("NUMBER_OF_PRODUCTS", ("SINGLE_PRODUCT",)))


def test_search_listings_passes_user_filters_through(mock_moto_calls, get_marketplace_listing_discovery_srv):
    get_marketplace_listing_discovery_srv.search_listings(
        search_text="ubuntu",
        category_filters=["cat-01", "cat-02"],
        pricing_model_filters=["FREE"],
        publisher_filters=["seller-test-01"],
        rating_filters=["4.0", "5.0"],
        next_token="tok-abc",
        max_results=10,
    )
    _, kwargs = mock_moto_calls["SearchListings"].call_args
    assertpy.assert_that(kwargs.get("searchText")).is_equal_to("ubuntu")
    assertpy.assert_that(kwargs.get("nextToken")).is_equal_to("tok-abc")
    assertpy.assert_that(kwargs.get("maxResults")).is_equal_to(10)
    filters = kwargs.get("filters", [])
    filter_types = {f["filterType"]: tuple(f["filterValues"]) for f in filters}
    assertpy.assert_that(filter_types["CATEGORY"]).is_equal_to(("cat-01", "cat-02"))
    assertpy.assert_that(filter_types["PRICING_MODEL"]).is_equal_to(("FREE",))
    assertpy.assert_that(filter_types["PUBLISHER"]).is_equal_to(("seller-test-01",))
    assertpy.assert_that(filter_types["AVERAGE_CUSTOMER_RATING"]).is_equal_to(("4.0", "5.0"))


def test_search_listings_ignores_blank_filter_values(mock_moto_calls, get_marketplace_listing_discovery_srv):
    """A query string like ?category=&rating= arrives as [""]. AWS rejects an empty
    filter value with ParamValidationError, which the API reported as a 500."""
    get_marketplace_listing_discovery_srv.search_listings(
        category_filters=[""],
        pricing_model_filters=["", "FREE"],
        publisher_filters=[" "],
        rating_filters=[],
    )
    _, kwargs = mock_moto_calls["SearchListings"].call_args
    filter_types = {f["filterType"]: f["filterValues"] for f in kwargs["filters"]}
    assertpy.assert_that(filter_types).does_not_contain_key("CATEGORY")
    assertpy.assert_that(filter_types).does_not_contain_key("PUBLISHER")
    assertpy.assert_that(filter_types).does_not_contain_key("AVERAGE_CUSTOMER_RATING")
    assertpy.assert_that(filter_types["PRICING_MODEL"]).is_equal_to(["FREE"])


def test_search_listings_caps_max_results(mock_moto_calls, get_marketplace_listing_discovery_srv):
    """maxResults is clamped to [1, 100] regardless of caller input."""
    get_marketplace_listing_discovery_srv.search_listings(max_results=10_000)
    _, kwargs = mock_moto_calls["SearchListings"].call_args
    assertpy.assert_that(kwargs.get("maxResults")).is_equal_to(100)

    mock_moto_calls["SearchListings"].reset_mock()
    get_marketplace_listing_discovery_srv.search_listings(max_results=0)
    _, kwargs = mock_moto_calls["SearchListings"].call_args
    assertpy.assert_that(kwargs.get("maxResults")).is_equal_to(1)


def test_get_listing_returns_full_detail_with_offer_id(mock_moto_calls, get_marketplace_listing_discovery_srv):
    result = get_marketplace_listing_discovery_srv.get_listing("prodview-testlisting01")

    mock_moto_calls["GetListing"].assert_called_once_with(listingId="prodview-testlisting01")
    assertpy.assert_that(result.listingId).is_equal_to("prodview-testlisting01")
    assertpy.assert_that(result.primaryOfferId).is_equal_to("offer-test01")
    assertpy.assert_that(result.primaryProductId).is_equal_to("prod-test01")
    assertpy.assert_that(result.longDescription).contains("Long description")
    assertpy.assert_that(len(result.highlights)).is_equal_to(2)
    assertpy.assert_that(len(result.resources)).is_equal_to(1)
    assertpy.assert_that(len(result.associatedEntities)).is_equal_to(1)


def test_get_listing_rejects_non_ami_fulfillment(
    mock_moto_calls, get_marketplace_listing_discovery_srv, mock_get_listing_response
):
    """AMI-only invariant is re-checked at the adapter boundary. A listing
    with only SaaS/Container fulfillment options must never reach domain
    code."""
    mock_get_listing_response["fulfillmentOptionSummaries"] = [{"fulfillmentOptionType": "SAAS", "displayName": "SaaS"}]
    mock_moto_calls["GetListing"].return_value = mock_get_listing_response

    from app.packaging.domain.exceptions.marketplace_request_rejected_exception import (
        MarketplaceRequestRejectedException,
    )

    with pytest.raises(MarketplaceRequestRejectedException) as excinfo:
        get_marketplace_listing_discovery_srv.get_listing("prodview-saas")
    assertpy.assert_that(str(excinfo.value)).contains("no AMI fulfillment option")


def test_search_facets_drops_non_exposed_facets(mock_moto_calls, get_marketplace_listing_discovery_srv):
    """PRICING_UNIT and DEPLOYED_ON_AWS are dropped by the adapter.
    Only CATEGORY, FULFILLMENT_OPTION_TYPE, PRICING_MODEL, PUBLISHER,
    AVERAGE_CUSTOMER_RATING are surfaced."""
    result = get_marketplace_listing_discovery_srv.search_facets()

    mock_moto_calls["SearchFacets"].assert_called_once()
    facet_names = set(result.facets.keys())
    assertpy.assert_that(facet_names).contains(
        "CATEGORY",
        "FULFILLMENT_OPTION_TYPE",
        "PRICING_MODEL",
        "PUBLISHER",
        "AVERAGE_CUSTOMER_RATING",
    )
    assertpy.assert_that(facet_names).does_not_contain("PRICING_UNIT")
    assertpy.assert_that(facet_names).does_not_contain("DEPLOYED_ON_AWS")
    assertpy.assert_that(result.totalResults).is_equal_to(10000)

    category_values = result.facets["CATEGORY"]
    assertpy.assert_that(len(category_values)).is_equal_to(2)
    assertpy.assert_that(category_values[1].parent).is_equal_to("cat-parent")


def test_search_listings_wraps_client_error_as_adapter_exception(
    mock_moto_calls, get_marketplace_listing_discovery_srv
):
    mock_moto_calls["SearchListings"].side_effect = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}},
        "SearchListings",
    )
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_listing_discovery_srv.search_listings()


def test_get_listing_rejects_an_unknown_listing_as_a_caller_error(
    mock_moto_calls, get_marketplace_listing_discovery_srv
):
    from app.packaging.domain.exceptions.marketplace_request_rejected_exception import (
        MarketplaceRequestRejectedException,
    )

    mock_moto_calls["GetListing"].side_effect = ClientError(
        {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}},
        "GetListing",
    )
    with pytest.raises(MarketplaceRequestRejectedException):
        get_marketplace_listing_discovery_srv.get_listing("prodview-missing")


def test_get_listing_wraps_a_service_error_as_adapter_exception(mock_moto_calls, get_marketplace_listing_discovery_srv):
    mock_moto_calls["GetListing"].side_effect = ClientError(
        {"Error": {"Code": "ThrottlingException", "Message": "slow down"}},
        "GetListing",
    )
    with pytest.raises(adapter_exception.AdapterException):
        get_marketplace_listing_discovery_srv.get_listing("prodview-1")
