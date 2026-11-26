from typing import Optional

from pydantic import ConfigDict, Field

from app.packaging.entrypoints.marketplace_agreement_event_handler.integration_events import shared_blocks
from app.shared.middleware import event_handler


class PurchaseAgreementCreatedAcceptor(event_handler.EventBase):
    """Buyer-side ``Purchase Agreement Created - Acceptor`` event payload.

    Received on ``detail`` of an ``aws.agreement-marketplace`` EventBridge
    event. Sent for three intents:

    - ``NEW`` — first-time agreement creation
    - ``REPLACE`` — private-offer replacement (ABO flow)
    - ``RENEW`` — auto-renewal at expiry

    Only ``RENEW`` events include ``agreement.previousAgreementId`` and a
    ``product`` block.
    """

    requestId: str = Field(...)
    catalog: str = Field(...)
    agreement: shared_blocks.AgreementBlock = Field(...)
    acceptor: shared_blocks.AccountBlock = Field(...)
    proposer: shared_blocks.AccountBlock = Field(...)
    offer: shared_blocks.OfferBlock = Field(...)
    product: Optional[shared_blocks.ProductBlock] = None
    model_config = ConfigDict(extra="allow")
