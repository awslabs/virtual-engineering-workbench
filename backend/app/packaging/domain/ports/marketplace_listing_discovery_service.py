from abc import ABC, abstractmethod
from typing import Optional

from app.packaging.domain.read_models.marketplace_listing import (
    MarketplaceFacetSet,
    MarketplaceListingDetail,
    MarketplaceListingSearchResult,
)


class MarketplaceListingDiscoveryService(ABC):
    """Read-side port for the AWS Marketplace ``marketplace-discovery``
    public-catalog surface used by in-VEW public browse.

    Only AMI listings are in scope; implementations MUST filter non-AMI
    fulfillment types at the API boundary, matching the equivalent invariant
    on active-agreement discovery. The ``AMAZON_MACHINE_IMAGE`` filter is
    applied server-side by the adapter and cannot be relaxed by callers.
    """

    @abstractmethod
    def search_listings(
        self,
        *,
        search_text: Optional[str] = None,
        category_filters: Optional[list[str]] = None,
        pricing_model_filters: Optional[list[str]] = None,
        publisher_filters: Optional[list[str]] = None,
        rating_filters: Optional[list[str]] = None,
        next_token: Optional[str] = None,
        max_results: int = 25,
    ) -> MarketplaceListingSearchResult:
        """Search the public catalog. Hard-locks
        ``FULFILLMENT_OPTION_TYPE=AMAZON_MACHINE_IMAGE`` and
        ``NUMBER_OF_PRODUCTS=SINGLE_PRODUCT``. Additional facet filters
        are user-supplied via kwargs and passed through unchanged.
        Raises ``AdapterException`` on AWS errors.
        """
        ...

    @abstractmethod
    def get_listing(self, listing_id: str) -> MarketplaceListingDetail:
        """Return full detail for a single listing, including
        ``primaryOfferId`` that bridges into the procurement flow.
        Raises ``AdapterException`` on missing / access-denied errors.
        """
        ...

    @abstractmethod
    def search_facets(self) -> MarketplaceFacetSet:
        """Return the available filter facets and their value counts. Used
        by the browse UI to render the filter sidebar. Only the facets
        useful for the AMI-only browse (CATEGORY, PRICING_MODEL, PUBLISHER,
        AVERAGE_CUSTOMER_RATING) are surfaced to callers; the adapter
        drops the others.
        """
        ...
