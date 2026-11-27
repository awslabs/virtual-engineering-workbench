from typing import Any

import boto3
from aws_lambda_powertools import logging
from botocore.exceptions import ClientError

from app.packaging.adapters.exceptions import adapter_exception
from app.packaging.domain.exceptions.marketplace_request_rejected_exception import MarketplaceRequestRejectedException
from app.packaging.domain.ports.marketplace_offer_discovery_service import MarketplaceOfferDiscoveryService
from app.packaging.domain.read_models.marketplace_offer import (
    MarketplaceOffer,
    MarketplaceOfferProductAssociation,
)
from app.packaging.domain.read_models.marketplace_offer_term import MarketplaceOfferTerm
from app.packaging.domain.read_models.marketplace_product_details import MarketplaceProductDetails
from app.packaging.domain.read_models.marketplace_purchase_option import MarketplacePurchaseOption

# An unknown or malformed id is the caller's error, so it is reported as a 400.
CALLER_ERROR_CODES = {"ResourceNotFoundException", "ValidationException"}

logger = logging.Logger()

MARKETPLACE_DISCOVERY = "marketplace-discovery"
# The Marketplace Discovery + Agreements APIs are only available in us-east-1
# regardless of the caller's home region.
MARKETPLACE_REGION = "us-east-1"
MARKETPLACE_CATALOG_NAME = "AWSMarketplace"

# ``ListPurchaseOptions`` requires at least one filter, and AWS accepts
# only ``PRIVATE`` as a ``VISIBILITY_SCOPE`` value (``PUBLIC`` is
# rejected). The valid combinations are:
#
#   * ``VISIBILITY_SCOPE=PRIVATE``       — list private offers extended
#                                          to the caller's account
#   * ``PRODUCT_ID=<id>``                — list offers for a specific product
#   * ``VISIBILITY_SCOPE=PRIVATE`` +
#     ``PRODUCT_ID=<id>``                — both, intersected
#
# Every other filter (``AVAILABILITY_STATUS``, ``SELLER_OF_RECORD_PROFILE_ID``,
# ``PURCHASE_OPTION_TYPE``) is rejected unless one of the above is also
# present. There is no way to enumerate the entire *public* Marketplace
# catalog from this API — it's a discovery surface for private /
# negotiated offers only. Public catalog browsing needs a different AWS
# API (``AWSMarketplaceCatalog.list_entities``) which is out of scope
# for procurement.
#
# Crucially, ``VISIBILITY_SCOPE`` limits *visibility*, not product type, and
# ``ListPurchaseOptions`` offers no fulfillment-option filter at all -- its
# ``filterType`` enum is PRODUCT_ID / SELLER_OF_RECORD_PROFILE_ID /
# PURCHASE_OPTION_TYPE / VISIBILITY_SCOPE / AVAILABILITY_STATUS in the
# botocore service model. Nor does the response carry
# a product type: ``associatedEntities[].product`` is
# {productId, productName, manufacturer}.
#
# So the AMI-only invariant this port declares has to be enforced by resolving
# each product through ``GetProduct`` and checking its fulfillment options.
# See ``_is_ami_product`` below.
#
DEFAULT_VISIBILITY_SCOPE = "PRIVATE"


class AwsMarketplaceOfferDiscoveryService(MarketplaceOfferDiscoveryService):
    """AWS-backed adapter for the buyer-side Discovery API surface
    (``ListPurchaseOptions`` / ``GetOffer`` / ``GetOfferTerms`` /
    ``GetProduct``).

    Together with :class:`AwsMarketplaceProcurementService` this forms the
    ports/adapters foundation of in-VEW Marketplace procurement.
    """

    def __init__(self, region: str, boto_session: Any = None):
        self._region = region
        self._boto_session = boto_session
        # Memoises GetProduct AMI-ness per distinct productId for the lifetime
        # of this adapter instance (i.e. one lambda invocation).
        self._ami_product_cache: dict[str, bool] = {}

    def _get_client(self):
        return (
            self._boto_session.client(MARKETPLACE_DISCOVERY, region_name=MARKETPLACE_REGION)
            if self._boto_session
            else boto3.client(MARKETPLACE_DISCOVERY, region_name=MARKETPLACE_REGION)
        )

    def list_purchase_options(self) -> list[MarketplacePurchaseOption]:
        """Return the AMI purchase options visible to the caller.

        The port contract is AMI-only, so non-AMI products are excluded here
        rather than left for the purchase-path guard to reject. The guard
        prevents the *purchase*, but anything returned from this method is
        rendered by the buyer UI as an AMI option -- so a Container or SaaS
        private offer reached the user as a choice they could select and only
        then be refused.
        """
        parsed: list[MarketplacePurchaseOption] = []
        next_token: str | None = None
        try:
            client = self._get_client()
            while True:
                kwargs: dict[str, Any] = {
                    "filters": [
                        {"filterType": "VISIBILITY_SCOPE", "filterValues": [DEFAULT_VISIBILITY_SCOPE]},
                    ],
                }
                if next_token:
                    kwargs["nextToken"] = next_token
                response = client.list_purchase_options(**kwargs)
                for summary in response.get("purchaseOptions", []):
                    parsed.extend(self._parse_purchase_option_summary(summary))
                next_token = response.get("nextToken")
                if not next_token:
                    break
        except ClientError as e:
            logger.warning("ListPurchaseOptions failed: %s", e)
            raise adapter_exception.AdapterException(f"Failed to list Marketplace purchase options: {e}")

        return [option for option in parsed if self._is_ami_product(option.productId)]

    def _is_ami_product(self, product_id: str) -> bool:
        """True when ``product_id`` has an AMI fulfillment option.

        Resolution requires one ``GetProduct`` call per distinct product,
        because neither ``ListPurchaseOptions``' filters nor its response
        expose a product type. Results are memoised per adapter instance so a
        catalogue containing several offers for the same product costs one
        call, not one per offer.

        A product that cannot be resolved is EXCLUDED. This port promises AMI
        products; on an ambiguous answer the honest output is to omit the row
        rather than present an unverified product to the buyer as an AMI. The
        failure is logged because a persistent AccessDenied here would quietly
        empty the list, and an empty list is otherwise indistinguishable from
        "no private offers".
        """
        if not product_id:
            return False
        cached = self._ami_product_cache.get(product_id)
        if cached is not None:
            return cached
        try:
            is_ami = self.get_product(product_id).is_ami_product()
        except adapter_exception.AdapterException as e:
            logger.warning(
                "Excluding purchase option: could not resolve product type for %s: %s",
                product_id,
                e,
            )
            is_ami = False
        self._ami_product_cache[product_id] = is_ami
        return is_ami

    def get_offer(self, offer_id: str) -> MarketplaceOffer:
        try:
            response = self._get_client().get_offer(offerId=offer_id)
        except ClientError as e:
            logger.warning("GetOffer(%s) failed: %s", offer_id, e)
            if e.response.get("Error", {}).get("Code") in CALLER_ERROR_CODES:
                raise MarketplaceRequestRejectedException(f"Marketplace offer {offer_id} cannot be read: {e}") from e
            raise adapter_exception.AdapterException(f"Failed to get Marketplace offer {offer_id}: {e}")
        seller = response.get("sellerOfRecord") if isinstance(response.get("sellerOfRecord"), dict) else None
        pricing = response.get("pricingModel") if isinstance(response.get("pricingModel"), dict) else None
        return MarketplaceOffer(
            offerId=response["offerId"],
            catalog=response.get("catalog", MARKETPLACE_CATALOG_NAME),
            offerName=response.get("offerName"),
            agreementProposalId=response["agreementProposalId"],
            sellerOfRecordDisplayName=seller.get("displayName") if seller else None,
            sellerOfRecordProfileId=seller.get("sellerProfileId") if seller else None,
            pricingModelType=pricing.get("pricingModelType") if pricing else None,
            pricingModelDisplayName=pricing.get("displayName") if pricing else None,
            expirationTime=self._iso_or_none(response.get("expirationTime")),
            availableFromTime=self._iso_or_none(response.get("availableFromTime")),
            replacementAgreementId=response.get("replacementAgreementId"),
            associatedProducts=self._parse_offer_associated_products(response.get("associatedEntities", [])),
        )

    def get_product(self, product_id: str) -> MarketplaceProductDetails:
        try:
            response = self._get_client().get_product(productId=product_id)
        except ClientError as e:
            logger.warning("GetProduct(%s) failed: %s", product_id, e)
            raise adapter_exception.AdapterException(f"Failed to get Marketplace product {product_id}: {e}")
        fulfillment_types = [
            summary.get("fulfillmentOptionType")
            for summary in response.get("fulfillmentOptionSummaries", [])
            if summary.get("fulfillmentOptionType")
        ]
        return MarketplaceProductDetails(
            productId=response["productId"],
            productName=response.get("productName"),
            fulfillmentOptionTypes=fulfillment_types,
        )

    # Complexity 9 (limit 8): pagination loop + defensive parsing of AWS's
    # single-key term-wrapper dict. Each branch handles a distinct AWS response
    # shape; splitting hurts readability more than it helps.
    def get_offer_terms(self, offer_id: str) -> list[MarketplaceOfferTerm]:  # noqa: C901
        terms: list[MarketplaceOfferTerm] = []
        next_token: str | None = None
        try:
            client = self._get_client()
            while True:
                kwargs: dict[str, Any] = {"offerId": offer_id}
                if next_token:
                    kwargs["nextToken"] = next_token
                response = client.get_offer_terms(**kwargs)
                for term in response.get("offerTerms", []):
                    # AWS returns each offer term as a single-key wrapper
                    # dict where the outer key is a camelCase alias (e.g.
                    # ``legalTerm``, ``fixedUpfrontPricingTerm``) and the
                    # inner payload carries both ``id`` and a ``type``
                    # discriminator (PascalCase, e.g. ``LegalTerm``,
                    # ``FixedUpfrontPricingTerm``). We prefer the inner
                    # ``type`` because it matches the Agreements API domain
                    # vocabulary used by ``CreateAgreementRequest`` term
                    # configurations, and we retain the raw payload for
                    # callers that need to build configurable-term
                    # configurations.
                    if not term:
                        continue
                    _, term_body = next(iter(term.items()))
                    if not isinstance(term_body, dict):
                        continue
                    terms.append(
                        MarketplaceOfferTerm(
                            termId=term_body.get("id", ""),
                            termType=term_body.get("type", ""),
                            rawTerm=term_body,
                        )
                    )
                next_token = response.get("nextToken")
                if not next_token:
                    break
        except ClientError as e:
            logger.warning("GetOfferTerms(%s) failed: %s", offer_id, e)
            raise adapter_exception.AdapterException(f"Failed to get terms for Marketplace offer {offer_id}: {e}")
        return terms

    @staticmethod
    def _iso_or_none(value: Any) -> str | None:
        """Convert a boto3 datetime to an ISO-8601 string, or ``None``.

        We deliberately return ``None`` (not ``str(value)``) for non-
        datetime input rather than letting garbage strings leak into the
        read model.
        """
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return None

    @staticmethod
    def _parse_offer_associated_products(
        associated_entities: list[dict[str, Any]],
    ) -> list[MarketplaceOfferProductAssociation]:
        """Flatten AWS ``GetOffer.associatedEntities`` into a domain-friendly
        list of product associations.

        Each entry has a required ``product`` structure (``productId``,
        ``productName``, ``manufacturer``) and an optional ``offerSet``
        grouping indicating this offer is part of a multi-product bundle.
        Bundles are rejected, so the ``partOfOfferSet`` flag is
        surfaced to the domain guard rather than being swallowed here.
        """
        results: list[MarketplaceOfferProductAssociation] = []
        for entity in associated_entities:
            if not isinstance(entity, dict):
                continue
            product = entity.get("product") if isinstance(entity.get("product"), dict) else None
            part_of_offer_set = "offerSet" in entity and entity.get("offerSet") is not None
            if not product:
                continue
            results.append(
                MarketplaceOfferProductAssociation(
                    productId=product.get("productId", ""),
                    productName=product.get("productName"),
                    partOfOfferSet=part_of_offer_set,
                )
            )
        return results

    @staticmethod
    def _parse_purchase_option_summary(
        summary: dict[str, Any],
    ) -> list[MarketplacePurchaseOption]:
        """Flatten one ``PurchaseOptionSummary`` into zero or more
        :class:`MarketplacePurchaseOption` entries.

        AWS returns purchase options with an ``associatedEntities`` list;
        each entry carries a ``product`` + ``offer`` + optional ``offerSet``.
        For a single-product offer we emit one entry. For a bundle
        (``OFFERSET``) we emit one entry per (product, offer) association
        with ``partOfOfferSet=True`` so the buyer UI can show the bundle
        and the domain guard can still reject it in the purchase path.
        """
        purchase_option_id = summary.get("purchaseOptionId")
        if not purchase_option_id:
            return []
        purchase_option_type = summary.get("purchaseOptionType") or "OFFER"
        catalog = summary.get("catalog", MARKETPLACE_CATALOG_NAME)
        seller = summary.get("sellerOfRecord") if isinstance(summary.get("sellerOfRecord"), dict) else None
        seller_display = seller.get("displayName") if seller else None
        available = AwsMarketplaceOfferDiscoveryService._iso_or_none(summary.get("availableFromTime"))
        expiration = AwsMarketplaceOfferDiscoveryService._iso_or_none(summary.get("expirationTime"))
        part_of_offer_set = purchase_option_type == "OFFERSET"

        results: list[MarketplacePurchaseOption] = []
        for entity in summary.get("associatedEntities", []):
            if not isinstance(entity, dict):
                continue
            product = entity.get("product") if isinstance(entity.get("product"), dict) else None
            offer = entity.get("offer") if isinstance(entity.get("offer"), dict) else None
            if not product or not offer:
                continue
            results.append(
                MarketplacePurchaseOption(
                    purchaseOptionId=purchase_option_id,
                    purchaseOptionType=purchase_option_type,
                    purchaseOptionName=summary.get("purchaseOptionName"),
                    catalog=catalog,
                    offerId=offer.get("offerId", ""),
                    productId=product.get("productId", ""),
                    productName=product.get("productName"),
                    sellerOfRecordDisplayName=seller_display,
                    availableFromTime=available,
                    expirationTime=expiration,
                    partOfOfferSet=part_of_offer_set,
                )
            )
        return results
