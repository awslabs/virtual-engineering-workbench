from typing import Optional

from pydantic import BaseModel, Field


class MarketplacePurchaseOption(BaseModel):
    """A single purchase option surfaced by the Discovery API
    ``ListPurchaseOptions`` call.

    Each purchase option is either an ``OFFER`` (single product, single
    offer) or an ``OFFERSET`` (bundle). Procurement is restricted to
    ``OFFER`` — bundles are rejected by the domain guard in
    ``CreateAgreementRequestCommand``.

    The fields exposed here are what the buyer UI needs to render a browse
    list; full detail (terms, pricing model, seller profile) is fetched via
    :meth:`MarketplaceOfferDiscoveryService.get_offer` when the buyer picks
    a specific option.

    ``offerId`` and ``productId`` are hoisted from the
    ``associatedEntities[]`` structure for callers that just want the two
    IDs; when a purchase option references multiple products (offer sets),
    the first entry is surfaced and ``partOfOfferSet`` is set to ``True``
    so the guard can reject early.
    """

    purchaseOptionId: str = Field(..., title="PurchaseOptionId")
    purchaseOptionType: str = Field(..., title="PurchaseOptionType")
    purchaseOptionName: Optional[str] = Field(None, title="PurchaseOptionName")
    catalog: str = Field(..., title="Catalog")
    offerId: str = Field(..., title="OfferId")
    productId: str = Field(..., title="ProductId")
    productName: Optional[str] = Field(None, title="ProductName")
    sellerOfRecordDisplayName: Optional[str] = Field(None, title="SellerOfRecordDisplayName")
    availableFromTime: Optional[str] = Field(None, title="AvailableFromTime")
    expirationTime: Optional[str] = Field(None, title="ExpirationTime")
    partOfOfferSet: bool = Field(False, title="PartOfOfferSet")
