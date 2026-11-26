from decimal import Decimal
from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class MarketplaceAgreementRenewalTermsFinalized(message_bus.Message):
    """Emitted when the Marketplace agreement event listener receives a
    ``Purchase Agreement Renewal Terms Finalized - Acceptor`` event. AWS
    emits this for percentage-range renewal offers once the seller's
    adjustment deadline has passed (renewal price uplift is now locked
    in, whether seller-adjusted or default).

    ``tcv`` is the total contract value AWS reports as a decimal string;
    we preserve exact precision by storing it as ``Decimal``.
    """

    event_name: Literal["MarketplaceAgreementRenewalTermsFinalized"] = Field(
        "MarketplaceAgreementRenewalTermsFinalized", alias="eventName"
    )
    agreementId: str = Field(..., title="agreementId")
    productId: Optional[str] = Field(None, title="productId")
    startTime: Optional[str] = Field(None, title="startTime")
    endTime: Optional[str] = Field(None, title="endTime")
    tcv: Optional[Decimal] = Field(None, title="tcv")
    currency: Optional[str] = Field(None, title="currency")
    termsFinalizedTime: Optional[str] = Field(None, title="termsFinalizedTime")
    lockoutReached: Optional[bool] = Field(None, title="lockoutReached")
    lockoutStartTime: Optional[str] = Field(None, title="lockoutStartTime")
    proposerAccountId: str = Field(..., title="proposerAccountId")
    acceptorAccountId: str = Field(..., title="acceptorAccountId")
    requestId: str = Field(..., title="requestId")
    catalog: str = Field(..., title="catalog")
    observedAt: str = Field(..., title="observedAt")
    model_config = ConfigDict(populate_by_name=True)
