from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class MarketplaceAgreementActivated(message_bus.Message):
    """Emitted when the Marketplace agreement event listener receives a
    ``Purchase Agreement Created - Acceptor`` event from AWS.

    The event corroborates a durable agreement now exists in the buyer's
    account. ``intent`` distinguishes first-time creation (``NEW``),
    private-offer replacement (``REPLACE``), and auto-renewal (``RENEW``).

    Note: AWS EventBridge events carry no VEW ``projectId``, and neither do
    ``AgreementRequestAccepted`` or ``AgreementCancelled``: an agreement
    belongs to the account, not to a project.
    """

    event_name: Literal["MarketplaceAgreementActivated"] = Field("MarketplaceAgreementActivated", alias="eventName")
    agreementId: str = Field(..., title="agreementId")
    offerId: str = Field(..., title="offerId")
    productId: Optional[str] = Field(None, title="productId")
    intent: Optional[str] = Field(None, title="intent")
    status: str = Field(..., title="status")
    startTime: Optional[str] = Field(None, title="startTime")
    endTime: Optional[str] = Field(None, title="endTime")
    acceptanceTime: Optional[str] = Field(None, title="acceptanceTime")
    previousAgreementId: Optional[str] = Field(None, title="previousAgreementId")
    proposerAccountId: str = Field(..., title="proposerAccountId")
    acceptorAccountId: str = Field(..., title="acceptorAccountId")
    requestId: str = Field(..., title="requestId")
    catalog: str = Field(..., title="catalog")
    observedAt: str = Field(..., title="observedAt")
    model_config = ConfigDict(populate_by_name=True)
