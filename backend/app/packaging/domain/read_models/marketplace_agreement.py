from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceAgreement(BaseModel):
    agreementId: str = Field(..., title="AgreementId")
    productId: str = Field(..., title="ProductId")
    offerId: str = Field(..., title="OfferId")
    status: str = Field(..., title="Status")
    acceptanceDate: Optional[str] = Field(None, title="AcceptanceDate")
    # Human-readable enrichment fields. Populated by
    # ``list_marketplace_agreements`` at the API handler layer via one
    # ``GetOffer`` call per agreement — the offer response also carries
    # the associated product's name, so no separate ``GetProduct`` call
    # is needed. These stay ``Optional`` so failure of a single per-row
    # enrichment call does not fail the entire list.
    productName: Optional[str] = Field(None, title="ProductName")
    offerName: Optional[str] = Field(None, title="OfferName")
    pricingModelType: Optional[str] = Field(None, title="PricingModelType")
