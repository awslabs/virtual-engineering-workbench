from abc import ABC, abstractmethod

from app.packaging.domain.read_models.marketplace_offer import MarketplaceOffer
from app.packaging.domain.read_models.marketplace_offer_term import MarketplaceOfferTerm
from app.packaging.domain.read_models.marketplace_product_details import MarketplaceProductDetails
from app.packaging.domain.read_models.marketplace_purchase_option import MarketplacePurchaseOption


class MarketplaceOfferDiscoveryService(ABC):
    """Read-side port for the AWS Marketplace Discovery API surface used by
    Marketplace procurement.

    Only AMI Marketplace products are in scope; implementations MUST filter
    non-AMI products at the API boundary, matching the equivalent invariant
    on active-agreement discovery.
    """

    @abstractmethod
    def list_purchase_options(self) -> list[MarketplacePurchaseOption]:
        """Return every AMI purchase option visible to the caller. Iterates
        Discovery API pagination internally.

        Implementations MUST exclude non-AMI products. The caller renders
        every returned row as an AMI option, so returning a Container or SaaS
        product here surfaces it to the buyer as something they can select --
        the downstream purchase guard then refuses it, which is a worse
        outcome than never offering it.

        A product whose type cannot be determined MUST be excluded rather than
        included optimistically.
        """
        ...

    @abstractmethod
    def get_offer(self, offer_id: str) -> MarketplaceOffer:
        """Return full detail for a single offer (proposal, seller, pricing
        model, availability window, and every product associated with the
        offer). Raises AdapterException on missing or access-denied errors.
        """
        ...

    @abstractmethod
    def get_offer_terms(self, offer_id: str) -> list[MarketplaceOfferTerm]:
        """Return every term attached to the offer. Callers pass a chosen
        subset of term IDs to :meth:`MarketplaceProcurementService.create_agreement_request`.
        """
        ...

    @abstractmethod
    def get_product(self, product_id: str) -> MarketplaceProductDetails:
        """Return product metadata for a single Marketplace product. Used by
        the ``CreateAgreementRequestCommand`` handler to verify the AMI-only
        invariant per-product (matches the pattern set by
        ``ImportImageCommand``, which re-validates the AMI's product code
        against AWS rather than trusting the caller).
        """
        ...
