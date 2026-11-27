from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceListingBadge(BaseModel):
    """Badge attached to a listing (e.g. Deployed on AWS, AWS Free Tier)."""

    badgeType: str = Field(..., title="BadgeType")
    displayName: str = Field(..., title="DisplayName")


class MarketplaceListingCategory(BaseModel):
    """A category tag on a listing. ``parent`` links a subcategory to its
    parent (e.g. Security under Infrastructure Software)."""

    categoryId: str = Field(..., title="CategoryId")
    displayName: str = Field(..., title="DisplayName")
    parent: Optional[str] = Field(None, title="Parent")


class MarketplaceListingPricingModel(BaseModel):
    """Pricing model summary tag on a listing (USAGE, CONTRACT, FREE, BYOL)."""

    pricingModelType: str = Field(..., title="PricingModelType")
    displayName: str = Field(..., title="DisplayName")


class MarketplaceListingFulfillmentOptionSummary(BaseModel):
    """Fulfillment option summary tag on a listing (AMI, SAAS, CONTAINER, ...)."""

    fulfillmentOptionType: str = Field(..., title="FulfillmentOptionType")
    displayName: str = Field(..., title="DisplayName")


class MarketplaceListingPublisher(BaseModel):
    """Publisher / manufacturer of a listing."""

    sellerProfileId: str = Field(..., title="SellerProfileId")
    displayName: str = Field(..., title="DisplayName")


class MarketplaceListingReviewSource(BaseModel):
    """Aggregated review from one source (typically AWS Marketplace)."""

    sourceId: str = Field(..., title="SourceId")
    sourceName: str = Field(..., title="SourceName")
    sourceUrl: Optional[str] = Field(None, title="SourceUrl")
    averageRating: Optional[str] = Field(None, title="AverageRating")
    totalReviews: Optional[int] = Field(None, title="TotalReviews")


class MarketplaceListingSummary(BaseModel):
    """A single listing surfaced by ``SearchListings``.

    AMI listings are hard-filtered at the adapter layer via
    ``FULFILLMENT_OPTION_TYPE=AMAZON_MACHINE_IMAGE``. Non-AMI listings
    should never reach this read model, but the schema itself is
    fulfillment-type-agnostic.
    """

    listingId: str = Field(..., title="ListingId")
    listingName: str = Field(..., title="ListingName")
    catalog: str = Field(..., title="Catalog")
    shortDescription: Optional[str] = Field(None, title="ShortDescription")
    logoThumbnailUrl: Optional[str] = Field(None, title="LogoThumbnailUrl")
    publisher: MarketplaceListingPublisher = Field(..., title="Publisher")
    categories: list[MarketplaceListingCategory] = Field(default_factory=list, title="Categories")
    fulfillmentOptionSummaries: list[MarketplaceListingFulfillmentOptionSummary] = Field(
        default_factory=list, title="FulfillmentOptionSummaries"
    )
    pricingModels: list[MarketplaceListingPricingModel] = Field(default_factory=list, title="PricingModels")
    badges: list[MarketplaceListingBadge] = Field(default_factory=list, title="Badges")
    reviewSummary: list[MarketplaceListingReviewSource] = Field(default_factory=list, title="ReviewSummary")
    # First associated product+offer, hoisted from ``associatedEntities`` for
    # convenience. The full array is available on ``GetListing`` output.
    primaryProductId: Optional[str] = Field(None, title="PrimaryProductId")
    primaryOfferId: Optional[str] = Field(None, title="PrimaryOfferId")


class MarketplaceListingSearchResult(BaseModel):
    """A single page of ``SearchListings`` results."""

    listings: list[MarketplaceListingSummary] = Field(default_factory=list, title="Listings")
    nextToken: Optional[str] = Field(None, title="NextToken")
    totalResults: Optional[int] = Field(None, title="TotalResults")


class MarketplaceListingResource(BaseModel):
    """A resource attached to a listing (link, doc, image)."""

    resourceType: str = Field(..., title="ResourceType")
    contentType: Optional[str] = Field(None, title="ContentType")
    value: Optional[str] = Field(None, title="Value")
    displayName: Optional[str] = Field(None, title="DisplayName")


class MarketplaceListingAssociatedEntity(BaseModel):
    """One (product, offer) pair associated with a listing. ``GetListing``
    typically returns exactly one entity for AMI listings; multi-product
    bundles return several and are filtered out at the browse layer
    (``NUMBER_OF_PRODUCTS=SINGLE_PRODUCT`` filter)."""

    productId: str = Field(..., title="ProductId")
    productName: str = Field(..., title="ProductName")
    productManufacturer: Optional[MarketplaceListingPublisher] = Field(None, title="ProductManufacturer")
    offerId: Optional[str] = Field(None, title="OfferId")
    offerSellerOfRecord: Optional[MarketplaceListingPublisher] = Field(None, title="OfferSellerOfRecord")


class MarketplaceListingDetail(BaseModel):
    """Full ``GetListing`` response. Used by the frontend to render a
    product-detail slide-over and (via ``primaryOfferId``) to bridge into
    the procurement wizard."""

    listingId: str = Field(..., title="ListingId")
    listingName: str = Field(..., title="ListingName")
    catalog: str = Field(..., title="Catalog")
    shortDescription: Optional[str] = Field(None, title="ShortDescription")
    longDescription: Optional[str] = Field(None, title="LongDescription")
    logoThumbnailUrl: Optional[str] = Field(None, title="LogoThumbnailUrl")
    publisher: MarketplaceListingPublisher = Field(..., title="Publisher")
    categories: list[MarketplaceListingCategory] = Field(default_factory=list, title="Categories")
    fulfillmentOptionSummaries: list[MarketplaceListingFulfillmentOptionSummary] = Field(
        default_factory=list, title="FulfillmentOptionSummaries"
    )
    pricingModels: list[MarketplaceListingPricingModel] = Field(default_factory=list, title="PricingModels")
    badges: list[MarketplaceListingBadge] = Field(default_factory=list, title="Badges")
    highlights: list[str] = Field(default_factory=list, title="Highlights")
    useCases: list[str] = Field(default_factory=list, title="UseCases")
    resources: list[MarketplaceListingResource] = Field(default_factory=list, title="Resources")
    associatedEntities: list[MarketplaceListingAssociatedEntity] = Field(
        default_factory=list, title="AssociatedEntities"
    )
    # Hoisted for convenience — the offerId of the first associated entity.
    # Frontend uses this to hand off to the procurement wizard.
    primaryOfferId: Optional[str] = Field(None, title="PrimaryOfferId")
    primaryProductId: Optional[str] = Field(None, title="PrimaryProductId")


class MarketplaceFacetValue(BaseModel):
    """A single value inside a facet (e.g. the AMAZON_MACHINE_IMAGE value
    inside the FULFILLMENT_OPTION_TYPE facet)."""

    value: str = Field(..., title="Value")
    displayName: str = Field(..., title="DisplayName")
    count: int = Field(..., title="Count")
    parent: Optional[str] = Field(None, title="Parent")


class MarketplaceFacetSet(BaseModel):
    """All available filter facets returned by ``SearchFacets``.

    Each key is a facet name (CATEGORY, FULFILLMENT_OPTION_TYPE,
    PRICING_MODEL, PRICING_UNIT, PUBLISHER, AVERAGE_CUSTOMER_RATING,
    DEPLOYED_ON_AWS, NUMBER_OF_PRODUCTS). Values are ordered by count
    descending as returned by AWS."""

    facets: dict[str, list[MarketplaceFacetValue]] = Field(default_factory=dict, title="Facets")
    totalResults: Optional[int] = Field(None, title="TotalResults")
