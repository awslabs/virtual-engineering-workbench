from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class MarketplaceAgreementEndingSoon(message_bus.Message):
    """Emitted when the Marketplace agreement event listener receives a
    ``Purchase Agreement Ending - Acceptor`` event. AWS sends these 180,
    120, 90, 60, and 30 days before an agreement's ``endTime``.

    ``daysBeforeEndTime`` matches the AWS-reported bucket and drives
    the buyer-facing expiry-warning badges in the frontend.
    """

    event_name: Literal["MarketplaceAgreementEndingSoon"] = Field("MarketplaceAgreementEndingSoon", alias="eventName")
    agreementId: str = Field(..., title="agreementId")
    offerId: str = Field(..., title="offerId")
    productId: Optional[str] = Field(None, title="productId")
    daysBeforeEndTime: int = Field(..., title="daysBeforeEndTime")
    status: str = Field(..., title="status")
    startTime: Optional[str] = Field(None, title="startTime")
    endTime: str = Field(..., title="endTime")
    autoRenewalEnabled: Optional[bool] = Field(None, title="autoRenewalEnabled")
    autoRenewalDisabledBy: Optional[str] = Field(None, title="autoRenewalDisabledBy")
    lockoutStartTime: Optional[str] = Field(None, title="lockoutStartTime")
    proposerAccountId: str = Field(..., title="proposerAccountId")
    acceptorAccountId: str = Field(..., title="acceptorAccountId")
    requestId: str = Field(..., title="requestId")
    catalog: str = Field(..., title="catalog")
    observedAt: str = Field(..., title="observedAt")
    model_config = ConfigDict(populate_by_name=True)
