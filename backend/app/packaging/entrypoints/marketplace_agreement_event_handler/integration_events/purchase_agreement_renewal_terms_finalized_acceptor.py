from typing import Optional

from pydantic import ConfigDict, Field

from app.packaging.entrypoints.marketplace_agreement_event_handler.integration_events import shared_blocks
from app.shared.middleware import event_handler


class PurchaseAgreementRenewalTermsFinalizedAcceptor(event_handler.EventBase):
    """Buyer-side ``Purchase Agreement Renewal Terms Finalized -
    Acceptor`` event payload.

    Emitted for percentage-range renewal offers after the seller's
    adjustment deadline; ``renewalSummary.tcv`` carries the finalized
    total contract value.
    """

    requestId: str = Field(...)
    catalog: str = Field(...)
    agreement: shared_blocks.AgreementBlock = Field(...)
    acceptor: shared_blocks.AccountBlock = Field(...)
    proposer: shared_blocks.AccountBlock = Field(...)
    product: Optional[shared_blocks.ProductBlock] = None
    renewalSummary: shared_blocks.RenewalSummaryBlock = Field(...)
    model_config = ConfigDict(extra="allow")
