from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class MarketplaceAgreementAmended(message_bus.Message):
    """Emitted when the Marketplace agreement event listener receives a
    ``Purchase Agreement Amended - Acceptor`` event. Amendments cover
    changes to terms, pricing, and buyer/seller auto-renewal
    opt-in/opt-out.

    ``autoRenewalDisabledBy`` is ``ACCEPTOR``, ``PROPOSER``, or ``None``
    (the last when auto-renewal is enabled or the term has no renewal).
    """

    event_name: Literal["MarketplaceAgreementAmended"] = Field("MarketplaceAgreementAmended", alias="eventName")
    agreementId: str = Field(..., title="agreementId")
    offerId: str = Field(..., title="offerId")
    productId: Optional[str] = Field(None, title="productId")
    intent: Optional[str] = Field(None, title="intent")
    status: str = Field(..., title="status")
    startTime: Optional[str] = Field(None, title="startTime")
    endTime: Optional[str] = Field(None, title="endTime")
    autoRenewalEnabled: Optional[bool] = Field(None, title="autoRenewalEnabled")
    autoRenewalDisabledBy: Optional[str] = Field(None, title="autoRenewalDisabledBy")
    lockoutStartTime: Optional[str] = Field(None, title="lockoutStartTime")
    proposerAccountId: str = Field(..., title="proposerAccountId")
    acceptorAccountId: str = Field(..., title="acceptorAccountId")
    requestId: str = Field(..., title="requestId")
    catalog: str = Field(..., title="catalog")
    observedAt: str = Field(..., title="observedAt")
    model_config = ConfigDict(populate_by_name=True)
