"""Click-time resolution of a Marketplace listing to an AMI.

The caller supplies a LISTING id; the service reads the listing back from
AWS (``GetListing``) to find the product id, then delegates to the
``AwsPublishedAmiResolverService`` for the (product -> AMI) step.

The only request this service refuses on its own is a multi-product bundle,
which has no single AMI to import. It does not gate on seller profile or
product id: the procurement wizard handles subscription state for every
seller, and the resolver is what decides whether an AMI can be identified.
A resolution with no candidates becomes a domain error here, so the UI
cannot offer an import with nothing behind it.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image.image_constants import ImageSource
from app.packaging.domain.ports.aws_published_ami_resolver_service import AwsPublishedAmiResolverService
from app.packaging.domain.ports.image_query_service import ImageQueryService
from app.packaging.domain.ports.marketplace_listing_discovery_service import MarketplaceListingDiscoveryService
from app.packaging.domain.read_models.aws_published_ami import AwsPublishedAmiCandidate
from app.packaging.domain.read_models.marketplace_listing import MarketplaceListingDetail
from app.packaging.domain.value_objects.shared import project_id_value_object

# AWS's seller profile. Informational only: the UI renders a "Sold by AWS"
# label from it, and nothing in this service branches on it. Same constant as
# frontend offer-helpers.ts AWS_SELLER_PROFILE_ID.
AWS_SELLER_PROFILE_ID = "e6a5002c-6dd0-4d1e-8196-0a1d1857229b"

IMPORTED_AMI_SOURCES = (ImageSource.MARKETPLACE_PRODUCT, ImageSource.AWS_PUBLISHED_AMI)


class AwsPublishedAmiResolutionResult(BaseModel):
    listingId: str = Field(..., title="ListingId")
    productId: str = Field(..., title="ProductId")
    productName: str = Field(..., title="ProductName")
    region: str = Field(..., title="Region")
    # True only when the resolver narrowed the listing to a single AMI.
    # The caller displays ``resolved`` when True and ``candidates`` otherwise.
    unambiguous: bool = Field(..., title="Unambiguous")
    resolved: Optional[AwsPublishedAmiCandidate] = Field(None, title="Resolved")
    candidates: list[AwsPublishedAmiCandidate] = Field(default_factory=list, title="Candidates")
    # AMI ids among ``candidates`` (and ``resolved``) already imported into
    # this project. Keyed on AMI id rather than product code, because the
    # no-product-code products have no code to key on.
    alreadyImportedAmiIds: list[str] = Field(default_factory=list, title="AlreadyImportedAmiIds")


class AwsPublishedAmiDomainQueryService:
    def __init__(
        self,
        listing_service: MarketplaceListingDiscoveryService,
        resolver: AwsPublishedAmiResolverService,
        image_qry_svc: ImageQueryService,
        hub_region: str,
        logger: logging.Logger,
    ) -> None:
        self._listing_service = listing_service
        self._resolver = resolver
        self._image_qry_svc = image_qry_svc
        self._hub_region = hub_region
        self._logger = logger

    def resolve_listing(
        self,
        project_id: project_id_value_object.ProjectIdValueObject,
        listing_id: str,
    ) -> AwsPublishedAmiResolutionResult:
        listing = self._listing_service.get_listing(listing_id)
        product_id = self._require_single_product(listing)

        resolution = self._resolver.resolve(product_id, self._hub_region)
        if not resolution.candidates:
            # Resolver logged why (no product code, no verified fallback, no
            # matching images). Surface as 400 so the UI cannot offer an
            # import with nothing behind it.
            raise domain_exception.DomainException(
                f"No AMI could be resolved for listing {listing_id} in {self._hub_region}. "
                "If this listing requires a Marketplace subscription, use the procurement wizard first."
            )

        imported = {
            img.imageUpstreamId
            for img in self._image_qry_svc.get_images(project_id.value)
            if img.imageSource in IMPORTED_AMI_SOURCES and img.imageUpstreamId
        }
        offered = {c.amiId for c in resolution.candidates}

        return AwsPublishedAmiResolutionResult(
            listingId=listing.listingId,
            productId=product_id,
            productName=listing.listingName or resolution.displayName,
            region=self._hub_region,
            unambiguous=resolution.unambiguous,
            resolved=resolution.resolved,
            # For an unambiguous product the resolved AMI is the answer; the
            # rest are older builds of the same image and are not shown.
            candidates=[] if resolution.resolved else resolution.candidates,
            alreadyImportedAmiIds=sorted(offered & imported),
        )

    @staticmethod
    def _require_single_product(listing: MarketplaceListingDetail) -> str:
        """Return the product id of a single-product Marketplace listing.

        Multi-product bundles are out of scope for AMI import. The resolver
        matches by product code, which identifies one AMI family per product,
        so a bundle listing has no coherent single AMI to import.
        """
        products = {e.productId for e in listing.associatedEntities if e.productId}
        if len(products) != 1:
            raise domain_exception.DomainException(
                f"Listing {listing.listingId} must reference exactly one product (found {len(products)})."
            )
        return products.pop()
