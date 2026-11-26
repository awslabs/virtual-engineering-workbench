from typing import Optional

from pydantic import ConfigDict, Field

from app.packaging.entrypoints.marketplace_agreement_event_handler.integration_events import shared_blocks
from app.shared.middleware import event_handler


class PurchaseAgreementRenewalUpcomingAcceptor(event_handler.EventBase):
    """Buyer-side ``Purchase Agreement Renewal Upcoming - Acceptor``
    event payload.

    Emitted at the start of the renewal-decision lockout period, once
    the renewal is confirmed to proceed.
    """

    requestId: str = Field(...)
    catalog: str = Field(...)
    agreement: shared_blocks.AgreementBlock = Field(...)
    acceptor: shared_blocks.AccountBlock = Field(...)
    proposer: shared_blocks.AccountBlock = Field(...)
    product: Optional[shared_blocks.ProductBlock] = None
    renewalSummary: shared_blocks.RenewalSummaryBlock = Field(...)
    model_config = ConfigDict(extra="allow")
