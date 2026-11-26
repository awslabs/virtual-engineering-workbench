from typing import Optional

from pydantic import ConfigDict, Field

from app.packaging.entrypoints.marketplace_agreement_event_handler.integration_events import shared_blocks
from app.shared.middleware import event_handler


class PurchaseAgreementEndingAcceptor(event_handler.EventBase):
    """Buyer-side ``Purchase Agreement Ending - Acceptor`` event payload.

    AWS emits at 180 / 120 / 90 / 60 / 30 days before ``agreement.endTime``.
    The specific bucket for this event is on
    ``agreement.daysBeforeEndTime``.
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
