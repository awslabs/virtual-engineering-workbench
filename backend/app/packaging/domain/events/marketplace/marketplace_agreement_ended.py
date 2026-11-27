from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class MarketplaceAgreementEnded(message_bus.Message):
    """Emitted when the Marketplace agreement event listener receives a
    ``Purchase Agreement Ended - Acceptor`` event. ``status`` is one of
    ``CANCELLED`` (buyer cancelled before end date), ``EXPIRED`` (reached
    defined end date), ``TERMINATED`` (AWS terminated, e.g. payment
    failure), ``RENEWED`` (rolled into new agreement), or ``REPLACED``
    (agreement-replacement offer).

    Downstream discovery-cache subscribers key off this event to
    drop the retired subscription.
    """

    event_name: Literal["MarketplaceAgreementEnded"] = Field("MarketplaceAgreementEnded", alias="eventName")
    agreementId: str = Field(..., title="agreementId")
    offerId: str = Field(..., title="offerId")
    status: str = Field(..., title="status")
    proposerAccountId: str = Field(..., title="proposerAccountId")
    acceptorAccountId: str = Field(..., title="acceptorAccountId")
    requestId: str = Field(..., title="requestId")
    catalog: str = Field(..., title="catalog")
    observedAt: str = Field(..., title="observedAt")
    model_config = ConfigDict(populate_by_name=True)
