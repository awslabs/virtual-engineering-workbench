from typing import Optional

from pydantic import BaseModel, Field


class MarketplaceAgreement(BaseModel):
    agreementId: str = Field(..., title="AgreementId")
    productId: str = Field(..., title="ProductId")
    offerId: str = Field(..., title="OfferId")
    status: str = Field(..., title="Status")
    acceptanceDate: Optional[str] = Field(None, title="AcceptanceDate")
