from typing import Optional

from pydantic import ConfigDict, Field

from app.packaging.entrypoints.marketplace_agreement_event_handler.integration_events import shared_blocks
from app.shared.middleware import event_handler


class PurchaseAgreementAmendedAcceptor(event_handler.EventBase):
    """Buyer-side ``Purchase Agreement Amended - Acceptor`` event payload.

    Received when the seller amends an active agreement (terms, pricing,
    auto-renewal opt-in/out).
    """

    requestId: str = Field(...)
    catalog: str = Field(...)
    agreement: shared_blocks.AgreementBlock = Field(...)
    acceptor: shared_blocks.AccountBlock = Field(...)
    proposer: shared_blocks.AccountBlock = Field(...)
    offer: shared_blocks.OfferBlock = Field(...)
    product: Optional[shared_blocks.ProductBlock] = None
    renewalSummary: Optional[shared_blocks.RenewalSummaryBlock] = None
    model_config = ConfigDict(extra="allow")
