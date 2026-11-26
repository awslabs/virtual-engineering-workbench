from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceOfferProductAssociation(BaseModel):
    """Product entity associated with a Marketplace Offer.

    The list of associations returned by ``GetOffer`` is used to enforce
    the AMI-only invariant on multi-product offer sets: any offer with a
    non-AMI product association is rejected at the domain-guard layer of
    ``CreateAgreementRequestCommand``. ``partOfOfferSet`` distinguishes true
    single-product offers from bundle offers, which cannot be bought.
    """

    productId: str = Field(..., title="ProductId")
    productName: Optional[str] = Field(None, title="ProductName")
    partOfOfferSet: bool = Field(False, title="PartOfOfferSet")


class MarketplaceOffer(BaseModel):
    """Full detail of a Marketplace Offer, fetched from the Discovery API
    ``GetOffer`` call. This is the entity the buyer sees when reviewing a
    quote before purchase.

    The AWS ``sellerOfRecord`` and ``pricingModel`` fields are nested
    structures (``{sellerProfileId, displayName}`` and
    ``{pricingModelType, displayName}`` respectively). We flatten them here
    into separate string fields so callers don't have to peek into dicts.
    """

    offerId: str = Field(..., title="OfferId")
    catalog: str = Field(..., title="Catalog")
    offerName: Optional[str] = Field(None, title="OfferName")
    agreementProposalId: str = Field(..., title="AgreementProposalId")
    sellerOfRecordDisplayName: Optional[str] = Field(None, title="SellerOfRecordDisplayName")
    sellerOfRecordProfileId: Optional[str] = Field(None, title="SellerOfRecordProfileId")
    pricingModelType: Optional[str] = Field(None, title="PricingModelType")
    pricingModelDisplayName: Optional[str] = Field(None, title="PricingModelDisplayName")
    expirationTime: Optional[str] = Field(None, title="ExpirationTime")
    availableFromTime: Optional[str] = Field(None, title="AvailableFromTime")
    replacementAgreementId: Optional[str] = Field(None, title="ReplacementAgreementId")
    associatedProducts: list[MarketplaceOfferProductAssociation] = Field(
        default_factory=list, title="AssociatedProducts"
    )
