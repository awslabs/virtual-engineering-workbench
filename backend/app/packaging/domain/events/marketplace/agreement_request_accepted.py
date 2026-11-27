from typing import Literal

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class AgreementRequestAccepted(message_bus.Message):
    """Emitted when a ``AcceptAgreementRequestCommand`` completes
    successfully. The durable ``agreementId`` is the buyer's subscription
    handle going forward. The ``aws.agreement-marketplace`` notification for
    the same agreement arrives separately, through the Marketplace agreement
    event listener, as ``MarketplaceAgreementActivated``.
    """

    event_name: Literal["AgreementRequestAccepted"] = Field("AgreementRequestAccepted", alias="eventName")
    agreementRequestId: str = Field(..., title="agreementRequestId")
    agreementId: str = Field(..., title="agreementId")
    acceptedAt: str = Field(..., title="acceptedAt")
    model_config = ConfigDict(populate_by_name=True)
