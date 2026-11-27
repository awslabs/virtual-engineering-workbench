from decimal import Decimal
from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class MarketplaceAgreementRenewalUpcoming(message_bus.Message):
    """Emitted when the Marketplace agreement event listener receives a
    ``Purchase Agreement Renewal Upcoming - Acceptor`` event. AWS emits
    this at the start of the renewal-decision lockout period, once the
    renewal is confirmed to proceed and the buyer can no longer opt out.
    """

    event_name: Literal["MarketplaceAgreementRenewalUpcoming"] = Field(
        "MarketplaceAgreementRenewalUpcoming", alias="eventName"
    )
    agreementId: str = Field(..., title="agreementId")
    productId: Optional[str] = Field(None, title="productId")
    startTime: Optional[str] = Field(None, title="startTime")
    endTime: Optional[str] = Field(None, title="endTime")
    tcv: Optional[Decimal] = Field(None, title="tcv")
    currency: Optional[str] = Field(None, title="currency")
    lockoutReached: Optional[bool] = Field(None, title="lockoutReached")
    proposerAccountId: str = Field(..., title="proposerAccountId")
    acceptorAccountId: str = Field(..., title="acceptorAccountId")
    requestId: str = Field(..., title="requestId")
    catalog: str = Field(..., title="catalog")
    observedAt: str = Field(..., title="observedAt")
    model_config = ConfigDict(populate_by_name=True)
