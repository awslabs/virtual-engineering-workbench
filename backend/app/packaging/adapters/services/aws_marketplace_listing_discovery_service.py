from typing import Any, Optional

import boto3
from aws_lambda_powertools import logging
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.exceptions.marketplace_request_rejected_exception import MarketplaceRequestRejectedException
from app.packaging.domain.ports.marketplace_listing_discovery_service import (
    MarketplaceListingDiscoveryService,
)
from app.packaging.domain.read_models.marketplace_listing import (
    MarketplaceFacetSet,
    MarketplaceFacetValue,
    MarketplaceListingAssociatedEntity,
    MarketplaceListingBadge,
    MarketplaceListingCategory,
    MarketplaceListingDetail,
    MarketplaceListingFulfillmentOptionSummary,
    MarketplaceListingPricingModel,
    MarketplaceListingPublisher,
    MarketplaceListingResource,
    MarketplaceListingReviewSource,
    MarketplaceListingSearchResult,
    MarketplaceListingSummary,
)

# An unknown or malformed id is the caller's error, so it is reported as a 400.
CALLER_ERROR_CODES = {"ResourceNotFoundException", "ValidationException"}

logger = logging.Logger()

MARKETPLACE_DISCOVERY = "marketplace-discovery"
# Same regional pin as ``aws_marketplace_offer_discovery_service`` — the
# discovery + agreement API surface is only available in us-east-1
# regardless of caller region.
MARKETPLACE_REGION = "us-east-1"
MARKETPLACE_CATALOG_NAME = "AWSMarketplace"

# AMI-only invariant. Applied server-side; cannot be overridden by callers.
FULFILLMENT_FILTER_TYPE = "FULFILLMENT_OPTION_TYPE"
FULFILLMENT_FILTER_VALUE_AMI = "AMAZON_MACHINE_IMAGE"

# Single-product listings only: bundles cannot be bought, because the
# quote guard rejects multi-product offers.
PRODUCT_COUNT_FILTER_TYPE = "NUMBER_OF_PRODUCTS"
PRODUCT_COUNT_FILTER_VALUE_SINGLE = "SINGLE_PRODUCT"

# User-supplied filter axes. Anything the frontend passes that isn't in
# this allow-list is dropped by the adapter — no free-form filter forwarding.
_ALLOWED_USER_FILTERS = frozenset({"CATEGORY", "PRICING_MODEL", "PUBLISHER", "AVERAGE_CUSTOMER_RATING"})

# Facets we expose to the frontend. Others (PRICING_UNIT, DEPLOYED_ON_AWS,
# NUMBER_OF_PRODUCTS — the last is locked, not user-selectable) are dropped.
_EXPOSED_FACETS = frozenset(_ALLOWED_USER_FILTERS | {"FULFILLMENT_OPTION_TYPE"})

_MAX_RESULTS_CAP = 100  # AWS API cap
_DEFAULT_MAX_RESULTS = 25


class AwsMarketplaceListingDiscoveryService(MarketplaceListingDiscoveryService):
    """boto3-backed implementation of
    :class:`MarketplaceListingDiscoveryService`.

    Uses ``marketplace-discovery`` — the same boto client
    :class:`AwsMarketplaceOfferDiscoveryService` uses for
    ``ListPurchaseOptions``. No cross-account calls, and no IAM scope beyond
    what procurement already required plus four ``marketplace-discovery``
    read actions.
    """

    def __init__(self, region: str, boto_session: Any = None) -> None:
        self._region = region
        self._boto_session = boto_session

    def _get_client(self) -> Any:
        return (
            self._boto_session.client(MARKETPLACE_DISCOVERY, region_name=MARKETPLACE_REGION)
            if self._boto_session
            else boto3.client(MARKETPLACE_DISCOVERY, region_name=MARKETPLACE_REGION)
        )

    # --- public API -----------------------------------------------------

    def search_listings(
        self,
        *,
        search_text: Optional[str] = None,
        category_filters: Optional[list[str]] = None,
        pricing_model_filters: Optional[list[str]] = None,
        publisher_filters: Optional[list[str]] = None,
        rating_filters: Optional[list[str]] = None,
        next_token: Optional[str] = None,
        max_results: int = _DEFAULT_MAX_RESULTS,
    ) -> MarketplaceListingSearchResult:
        # Cap max_results and enforce a floor of 1. ``None`` falls back to
        # the default; explicit ``0`` or negative gets floored to 1.
        if max_results is None:
            max_results = _DEFAULT_MAX_RESULTS
        max_results = max(1, min(int(max_results), _MAX_RESULTS_CAP))

        filters: list[dict[str, Any]] = [
            {"filterType": FULFILLMENT_FILTER_TYPE, "filterValues": [FULFILLMENT_FILTER_VALUE_AMI]},
            {"filterType": PRODUCT_COUNT_FILTER_TYPE, "filterValues": [PRODUCT_COUNT_FILTER_VALUE_SINGLE]},
        ]
        for facet_type, values in (
            ("CATEGORY", category_filters),
            ("PRICING_MODEL", pricing_model_filters),
            ("PUBLISHER", publisher_filters),
            ("AVERAGE_CUSTOMER_RATING", rating_filters),
        ):
            # A blank value ("?category=") means no filter. AWS rejects an empty
            # filter value, which would otherwise surface as a 500.
            present = [v for v in (values or []) if v and v.strip()]
            if present:
                filters.append({"filterType": facet_type, "filterValues": present})

        kwargs: dict[str, Any] = {"filters": filters, "maxResults": max_results}
        if search_text:
            kwargs["searchText"] = search_text
        if next_token:
            kwargs["nextToken"] = next_token

        try:
            client = self._get_client()
            response = client.search_listings(**kwargs)
        except ClientError as e:
            logger.warning("SearchListings failed: %s", e)
            raise adapter_exception.AdapterException(f"Failed to search Marketplace listings: {e}")

        listings = [self._parse_listing_summary(item) for item in response.get("listingSummaries", [])]
        return MarketplaceListingSearchResult(
            listings=listings,
            nextToken=response.get("nextToken"),
            totalResults=response.get("totalResults"),
        )

    def get_listing(self, listing_id: str) -> MarketplaceListingDetail:
        try:
            client = self._get_client()
            response = client.get_listing(listingId=listing_id)
        except ClientError as e:
            logger.warning("GetListing(%s) failed: %s", listing_id, e)
            if e.response.get("Error", {}).get("Code") in CALLER_ERROR_CODES:
                raise MarketplaceRequestRejectedException(
                    f"Marketplace listing {listing_id} cannot be read: {e}"
                ) from e
            raise adapter_exception.AdapterException(f"Failed to get Marketplace listing {listing_id}: {e}")

        associated = [self._parse_associated_entity(e) for e in response.get("associatedEntities", [])]
        primary_offer_id = associated[0].offerId if associated else None
        primary_product_id = associated[0].productId if associated else None

        # AMI-only invariant re-checked at the boundary. If a caller crafts
        # a listing_id for a SaaS/Container listing, we surface it as a 4xx
        # rather than silently returning non-AMI data.
        fulfillment_types = {
            fo.get("fulfillmentOptionType") for fo in response.get("fulfillmentOptionSummaries", []) if fo
        }
        if fulfillment_types and FULFILLMENT_FILTER_VALUE_AMI not in fulfillment_types:
            raise MarketplaceRequestRejectedException(
                f"Listing {listing_id} has no AMI fulfillment option "
                f"(has: {sorted(fulfillment_types)}). VEW only supports AMI listings today."
            )

        return MarketplaceListingDetail(
            listingId=response.get("listingId") or listing_id,
            listingName=response.get("listingName", ""),
            catalog=response.get("catalog", MARKETPLACE_CATALOG_NAME),
            shortDescription=response.get("shortDescription"),
            longDescription=response.get("longDescription"),
            logoThumbnailUrl=response.get("logoThumbnailUrl"),
            publisher=self._parse_publisher(response.get("publisher", {})),
            categories=[self._parse_category(c) for c in response.get("categories", [])],
            fulfillmentOptionSummaries=[
                self._parse_fulfillment_summary(fo) for fo in response.get("fulfillmentOptionSummaries", [])
            ],
            pricingModels=[self._parse_pricing_model(pm) for pm in response.get("pricingModels", [])],
            badges=[self._parse_badge(b) for b in response.get("badges", [])],
            highlights=list(response.get("highlights", []) or []),
            useCases=list(response.get("useCases", []) or []),
            resources=[self._parse_resource(r) for r in response.get("resources", [])],
            associatedEntities=associated,
            primaryOfferId=primary_offer_id,
            primaryProductId=primary_product_id,
        )

    def search_facets(self) -> MarketplaceFacetSet:
        try:
            client = self._get_client()
            response = client.search_facets()
        except ClientError as e:
            logger.warning("SearchFacets failed: %s", e)
            raise adapter_exception.AdapterException(f"Failed to fetch Marketplace facets: {e}")

        facets: dict[str, list[MarketplaceFacetValue]] = {}
        for facet_name, values in (response.get("listingFacets") or {}).items():
            if facet_name not in _EXPOSED_FACETS:
                continue
            facets[facet_name] = [
                MarketplaceFacetValue(
                    value=v.get("value", ""),
                    displayName=v.get("displayName", ""),
                    count=int(v.get("count", 0)),
                    parent=v.get("parent"),
                )
                for v in (values or [])
                if v and v.get("value")
            ]
        return MarketplaceFacetSet(facets=facets, totalResults=response.get("totalResults"))

    # --- parsers --------------------------------------------------------

    @staticmethod
    def _parse_publisher(payload: dict[str, Any]) -> MarketplaceListingPublisher:
        return MarketplaceListingPublisher(
            sellerProfileId=payload.get("sellerProfileId", ""),
            displayName=payload.get("displayName", ""),
        )

    @staticmethod
    def _parse_category(payload: dict[str, Any]) -> MarketplaceListingCategory:
        return MarketplaceListingCategory(
            categoryId=payload.get("categoryId", ""),
            displayName=payload.get("displayName", ""),
            parent=payload.get("parent"),
        )

    @staticmethod
    def _parse_pricing_model(payload: dict[str, Any]) -> MarketplaceListingPricingModel:
        return MarketplaceListingPricingModel(
            pricingModelType=payload.get("pricingModelType", ""),
            displayName=payload.get("displayName", ""),
        )

    @staticmethod
    def _parse_badge(payload: dict[str, Any]) -> MarketplaceListingBadge:
        return MarketplaceListingBadge(
            badgeType=payload.get("badgeType", ""),
            displayName=payload.get("displayName", ""),
        )

    @staticmethod
    def _parse_fulfillment_summary(payload: dict[str, Any]) -> MarketplaceListingFulfillmentOptionSummary:
        return MarketplaceListingFulfillmentOptionSummary(
            fulfillmentOptionType=payload.get("fulfillmentOptionType", ""),
            displayName=payload.get("displayName", ""),
        )

    @staticmethod
    def _parse_resource(payload: dict[str, Any]) -> MarketplaceListingResource:
        return MarketplaceListingResource(
            resourceType=payload.get("resourceType", ""),
            contentType=payload.get("contentType"),
            value=payload.get("value"),
            displayName=payload.get("displayName"),
        )

    @classmethod
    def _parse_review_summary(cls, payload: dict[str, Any]) -> list[MarketplaceListingReviewSource]:
        return [
            MarketplaceListingReviewSource(
                sourceId=src.get("sourceId", ""),
                sourceName=src.get("sourceName", ""),
                sourceUrl=src.get("sourceUrl"),
                averageRating=str(src["averageRating"]) if src.get("averageRating") is not None else None,
                totalReviews=int(src["totalReviews"]) if src.get("totalReviews") is not None else None,
            )
            for src in (payload.get("reviewSourceSummaries") or [])
            if src
        ]

    @classmethod
    def _parse_associated_entity(cls, payload: dict[str, Any]) -> MarketplaceListingAssociatedEntity:
        product = payload.get("product") or {}
        offer = payload.get("offer") or {}
        return MarketplaceListingAssociatedEntity(
            productId=product.get("productId", ""),
            productName=product.get("productName", ""),
            productManufacturer=(
                cls._parse_publisher(product["manufacturer"]) if product.get("manufacturer") else None
            ),
            offerId=offer.get("offerId"),
            offerSellerOfRecord=(
                cls._parse_publisher(offer["sellerOfRecord"]) if offer.get("sellerOfRecord") else None
            ),
        )

    @classmethod
    def _parse_listing_summary(cls, payload: dict[str, Any]) -> MarketplaceListingSummary:
        associated = [cls._parse_associated_entity(e) for e in payload.get("associatedEntities", [])]
        primary_offer_id = None
        primary_product_id = None
        if associated:
            primary_offer_id = associated[0].offerId
            primary_product_id = associated[0].productId
        return MarketplaceListingSummary(
            listingId=payload.get("listingId", ""),
            listingName=payload.get("listingName", ""),
            catalog=payload.get("catalog", MARKETPLACE_CATALOG_NAME),
            shortDescription=payload.get("shortDescription"),
            logoThumbnailUrl=payload.get("logoThumbnailUrl"),
            publisher=cls._parse_publisher(payload.get("publisher", {})),
            categories=[cls._parse_category(c) for c in payload.get("categories", [])],
            fulfillmentOptionSummaries=[
                cls._parse_fulfillment_summary(fo) for fo in payload.get("fulfillmentOptionSummaries", [])
            ],
            pricingModels=[cls._parse_pricing_model(pm) for pm in payload.get("pricingModels", [])],
            badges=[cls._parse_badge(b) for b in payload.get("badges", [])],
            reviewSummary=cls._parse_review_summary(payload.get("reviewSummary") or {}),
            primaryProductId=primary_product_id,
            primaryOfferId=primary_offer_id,
        )
