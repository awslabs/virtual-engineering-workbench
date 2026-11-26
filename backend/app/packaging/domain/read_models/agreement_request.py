from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class AgreementChargeSummary(BaseModel):
    """Estimated charges returned by the Agreements API
    ``CreateAgreementRequest`` call. Presented to the buyer as the "quote"
    before they confirm purchase.

    Field names mirror the AWS ``ChargeSummary`` shape. AWS returns the
    amounts as ``BoundedString`` (strings that may or may not parse to a
    Decimal); the adapter coerces defensively and drops unparseable values
    to ``None`` rather than propagating garbage.

    Note: for pure usage-based pricing (AMI/container hourly), AWS returns
    ``newAgreementValue = 0`` — see the AWS ``EstimatedCharges``
    documentation for the full nuance. The frontend should render "See
    usage-based pricing details" rather than "Charged: $0.00" when the
    accepted terms are usage-based only.
    """

    newAgreementValue: Optional[Decimal] = Field(None, title="NewAgreementValue")
    newAgreementValueAfterTax: Optional[Decimal] = Field(None, title="NewAgreementValueAfterTax")
    currencyCode: Optional[str] = Field(None, title="CurrencyCode")


class AgreementRequestQuote(BaseModel):
    """Result of a successful Agreements API ``CreateAgreementRequest``
    call.

    The ``agreementRequestId`` is a short-lived handle (typically minutes
    to hours) that the buyer confirms via ``AcceptAgreementRequest``. Do
    not persist long-term.
    """

    agreementRequestId: str = Field(..., title="AgreementRequestId")
    chargeSummary: Optional[AgreementChargeSummary] = Field(None, title="ChargeSummary")


class AcceptedAgreement(BaseModel):
    """Result of a successful Agreements API ``AcceptAgreementRequest``
    call.

    Contains the durable ``agreementId`` that identifies the buyer's
    subscription going forward.
    """

    agreementId: str = Field(..., title="AgreementId")
