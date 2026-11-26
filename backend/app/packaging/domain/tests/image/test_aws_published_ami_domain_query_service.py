"""Tests for AwsPublishedAmiDomainQueryService.

The service does four things and these tests pin each of them: read the
listing and refuse a multi-product bundle, delegate resolution to the
resolver port, join the result with the AMIs already imported into the
project, and turn a resolution with no candidates into a DomainException so
the UI cannot offer an import with nothing behind it.

It deliberately has no seller gate and no product allowlist. The procurement
wizard handles subscription state for every seller, and the resolver is the
only thing that decides whether an AMI can be identified, so a test that
expects a listing to be refused on its seller or its product id would be
pinning behaviour this service does not have.
"""

import logging
from unittest import mock

import assertpy
import pytest

from app.packaging.domain.exceptions import domain_exception
from app.packaging.domain.model.image import image
from app.packaging.domain.model.image.image_constants import ImageSource
from app.packaging.domain.ports.aws_published_ami_resolver_service import AwsPublishedAmiResolverService
from app.packaging.domain.ports.image_query_service import ImageQueryService
from app.packaging.domain.ports.marketplace_listing_discovery_service import MarketplaceListingDiscoveryService
from app.packaging.domain.query_services.aws_published_ami_domain_query_service import (
    AWS_SELLER_PROFILE_ID,
    AwsPublishedAmiDomainQueryService,
)
from app.packaging.domain.read_models.aws_published_ami import (
    AwsPublishedAmiCandidate,
    AwsPublishedAmiResolution,
)
from app.packaging.domain.read_models.marketplace_listing import (
    MarketplaceListingAssociatedEntity,
    MarketplaceListingDetail,
    MarketplaceListingPublisher,
)
from app.packaging.domain.value_objects.shared import project_id_value_object

# Canonical's profile, a real non-AWS seller. The service must delegate such
# a listing to the resolver like any other, rather than refusing it.
CANONICAL_PROFILE_ID = "50c8dca0-a060-4e40-b30a-b612e829b2a3"

PROJECT = project_id_value_object.from_str("proj-1")
RHEL9 = "02bec9ca-1c81-40ac-83a2-aa021e2a0b39"
ROCKY9 = "3f230a17-9877-4b16-aa5e-b1ff34ab206b"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def _listing(publisher=AWS_SELLER_PROFILE_ID, offer_seller=AWS_SELLER_PROFILE_ID, products=(RHEL9,)):
    aws = MarketplaceListingPublisher(sellerProfileId=publisher, displayName="Amazon Web Services")
    return MarketplaceListingDetail(
        listingId="listing-1",
        listingName="Red Hat Enterprise Linux 9",
        catalog="AWSMarketplace",
        publisher=aws,
        associatedEntities=[
            MarketplaceListingAssociatedEntity(
                productId=p,
                productName="RHEL 9",
                offerId="offer-1",
                offerSellerOfRecord=MarketplaceListingPublisher(
                    sellerProfileId=offer_seller, displayName="Amazon Web Services"
                ),
            )
            for p in products
        ],
    )


def _candidate(ami_id, name=None, arch="x86_64", usage_op="RunInstances:0010"):
    return AwsPublishedAmiCandidate(
        amiId=ami_id,
        amiName=name or f"{ami_id}-name",
        ownerId="309956199498",
        architecture=arch,
        platformDetails="Red Hat Enterprise Linux",
        usageOperation=usage_op,
        creationDate="2026-10-01T00:00:00.000Z",
        region="us-east-1",
    )


@pytest.fixture
def deps():
    listing_svc = mock.NonCallableMagicMock(spec=MarketplaceListingDiscoveryService)
    resolver = mock.NonCallableMagicMock(spec=AwsPublishedAmiResolverService)
    image_svc = mock.NonCallableMagicMock(spec=ImageQueryService)
    image_svc.get_images.return_value = []
    svc = AwsPublishedAmiDomainQueryService(
        listing_service=listing_svc,
        resolver=resolver,
        image_qry_svc=image_svc,
        hub_region="us-east-1",
        logger=logging.getLogger("test"),
    )
    return svc, listing_svc, resolver, image_svc


# ---------------------------------------------------------------------------
# happy paths
# ---------------------------------------------------------------------------


def test_resolves_an_aws_sold_listing_via_the_resolver(deps):
    svc, listing_svc, resolver, _ = deps
    listing_svc.get_listing.return_value = _listing()
    resolver.resolve.return_value = AwsPublishedAmiResolution(
        productId=RHEL9, unambiguous=True, candidates=[_candidate("ami-rhel9")]
    )

    result = svc.resolve_listing(PROJECT, "listing-1")

    assertpy.assert_that(result.unambiguous).is_true()
    assertpy.assert_that(result.resolved.amiId).is_equal_to("ami-rhel9")
    resolver.resolve.assert_called_once_with(RHEL9, "us-east-1")


def test_resolves_a_non_aws_seller_listing_without_refusing(deps):
    """A Canonical-sold or Rocky-sold listing is delegated to the resolver
    like any other. There is no seller-of-record gate: whether the account
    needs a subscription for the product is the procurement wizard's
    concern, and refusing here would hide products a user can legitimately
    import."""
    svc, listing_svc, resolver, _ = deps
    listing_svc.get_listing.return_value = _listing(
        publisher=CANONICAL_PROFILE_ID, offer_seller=CANONICAL_PROFILE_ID, products=(ROCKY9,)
    )
    resolver.resolve.return_value = AwsPublishedAmiResolution(
        productId=ROCKY9, unambiguous=True, candidates=[_candidate("ami-rocky", "Rocky-9-EC2-Base")]
    )

    result = svc.resolve_listing(PROJECT, "listing-1")

    assertpy.assert_that(result.unambiguous).is_true()
    assertpy.assert_that(result.resolved.amiId).is_equal_to("ami-rocky")
    # The listing was not refused on its seller: delegation did happen.
    resolver.resolve.assert_called_once_with(ROCKY9, "us-east-1")


def test_resolves_an_aws_sold_product_coded_listing(deps):
    """RHEL-SAP is AWS-sold and its AMI carries a product code, so it
    resolves through the resolver's product-code path without needing an
    entry in the no-product-code table. The service passes it through
    unchanged."""
    svc, listing_svc, resolver, _ = deps
    rhel_sap = "0d9c685f-9ed6-4f32-9709-a93ab9680b74"
    listing_svc.get_listing.return_value = _listing(products=(rhel_sap,))
    resolver.resolve.return_value = AwsPublishedAmiResolution(
        productId=rhel_sap,
        unambiguous=True,
        candidates=[_candidate("ami-rhelsap", "RHEL-SAP-9.2-x86_64")],
    )

    result = svc.resolve_listing(PROJECT, "listing-1")
    assertpy.assert_that(result.resolved.amiId).is_equal_to("ami-rhelsap")


def test_flags_amis_already_imported_into_this_project(deps):
    svc, listing_svc, resolver, image_svc = deps
    listing_svc.get_listing.return_value = _listing()
    resolver.resolve.return_value = AwsPublishedAmiResolution(
        productId=RHEL9,
        unambiguous=False,
        candidates=[_candidate("ami-a"), _candidate("ami-b"), _candidate("ami-c")],
    )
    img_a = mock.MagicMock(spec=image.Image)
    img_a.imageSource = ImageSource.AWS_PUBLISHED_AMI
    img_a.imageUpstreamId = "ami-a"
    img_c = mock.MagicMock(spec=image.Image)
    img_c.imageSource = ImageSource.MARKETPLACE_PRODUCT
    img_c.imageUpstreamId = "ami-c"
    image_svc.get_images.return_value = [img_a, img_c]

    result = svc.resolve_listing(PROJECT, "listing-1")

    assertpy.assert_that(result.alreadyImportedAmiIds).is_equal_to(["ami-a", "ami-c"])


# ---------------------------------------------------------------------------
# refusal paths
# ---------------------------------------------------------------------------


def test_multi_product_listing_is_refused_before_calling_the_resolver(deps):
    """Bundle listings cannot be imported as a single AMI. The service
    refuses before the resolver runs."""
    svc, listing_svc, resolver, _ = deps
    listing_svc.get_listing.return_value = _listing(products=(RHEL9, ROCKY9))

    with pytest.raises(domain_exception.DomainException, match="exactly one product"):
        svc.resolve_listing(PROJECT, "listing-1")

    resolver.resolve.assert_not_called()


def test_unresolved_product_raises_a_domain_error(deps):
    """When the resolver identifies no AMI (no product code and no fallback
    entry), the service surfaces it as a domain error rather than returning
    an empty success the UI would render as an importable listing."""
    svc, listing_svc, resolver, _ = deps
    listing_svc.get_listing.return_value = _listing()
    resolver.resolve.return_value = AwsPublishedAmiResolution(productId=RHEL9, unambiguous=False, candidates=[])

    with pytest.raises(domain_exception.DomainException, match="No AMI could be resolved"):
        svc.resolve_listing(PROJECT, "listing-1")


def test_ambiguous_resolution_returns_candidates_without_resolved(deps):
    """When the resolver offers more than one architecture it cannot pick a
    single image, so the result carries candidates and resolved is None and
    the caller presents a chooser."""
    svc, listing_svc, resolver, _ = deps
    listing_svc.get_listing.return_value = _listing()
    resolver.resolve.return_value = AwsPublishedAmiResolution(
        productId=RHEL9,
        unambiguous=False,
        candidates=[_candidate("ami-a"), _candidate("ami-b")],
    )

    result = svc.resolve_listing(PROJECT, "listing-1")

    assertpy.assert_that(result.resolved).is_none()
    assertpy.assert_that(len(result.candidates)).is_equal_to(2)
