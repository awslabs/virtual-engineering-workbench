from pydantic import ConfigDict, Field

from app.packaging.entrypoints.marketplace_agreement_event_handler.integration_events import shared_blocks
from app.shared.middleware import event_handler


class PurchaseAgreementEndedAcceptor(event_handler.EventBase):
    """Buyer-side ``Purchase Agreement Ended - Acceptor`` event payload.

    ``agreement.status`` distinguishes the ending reason (``CANCELLED``,
    ``EXPIRED``, ``TERMINATED``, ``RENEWED``, ``REPLACED``).
    """

    requestId: str = Field(...)
    catalog: str = Field(...)
    agreement: shared_blocks.AgreementBlock = Field(...)
    acceptor: shared_blocks.AccountBlock = Field(...)
    proposer: shared_blocks.AccountBlock = Field(...)
    offer: shared_blocks.OfferBlock = Field(...)
    model_config = ConfigDict(extra="allow")
