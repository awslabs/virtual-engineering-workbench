from decimal import Decimal
from typing import Literal, Optional

from pydantic import ConfigDict, Field

from app.shared.adapters.message_bus import message_bus


class AgreementRequestCreated(message_bus.Message):
    """Emitted when a ``CreateAgreementRequestCommand`` completes
    successfully. The short-lived ``agreementRequestId`` is the buyer's
    handle on the quote pending confirmation.

    The estimated-charge fields mirror AWS's ``ChargeSummary`` shape and
    may all be ``None`` for pure usage-based pricing (AMI hourly), where
    AWS does not know the total cost up front.
    """

    event_name: Literal["AgreementRequestCreated"] = Field("AgreementRequestCreated", alias="eventName")
    projectId: str = Field(..., title="projectId")
    agreementRequestId: str = Field(..., title="agreementRequestId")
    offerId: str = Field(..., title="offerId")
    agreementProposalId: str = Field(..., title="agreementProposalId")
    estimatedAgreementValue: Optional[Decimal] = Field(None, title="estimatedAgreementValue")
    estimatedAgreementValueAfterTax: Optional[Decimal] = Field(None, title="estimatedAgreementValueAfterTax")
    estimatedCurrencyCode: Optional[str] = Field(None, title="estimatedCurrencyCode")
    createdAt: str = Field(..., title="createdAt")
    model_config = ConfigDict(populate_by_name=True)
