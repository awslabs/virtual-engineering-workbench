from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AgreementBlock(BaseModel):
    """Nested ``detail.agreement`` block on a Marketplace agreement event.

    Not every field is present on every event type:

    - ``intent`` appears on Created (``NEW`` | ``REPLACE`` | ``RENEW``)
      and Amended (``AMEND``); absent on Ended / Ending / Renewal events.
    - ``status`` is present on Created, Amended, Ended, and Ending; AWS
      omits it on ``Renewal Terms Finalized`` and ``Renewal Upcoming``
      (only ``id``, ``startTime``, ``endTime`` are documented on those
      two shapes).
    - ``acceptanceTime`` / ``startTime`` / ``endTime`` are only present on
      Created / Amended / Ending / Renewal; Ended events carry only ``status``.
    - ``daysBeforeEndTime`` is unique to Ending.
    - ``autoRenewalEnabled`` appears on Amended and Ending.
    - ``previousAgreementId`` is present only on ``RENEW`` events.
    """

    id: str = Field(...)
    intent: Optional[str] = None
    status: Optional[str] = None
    acceptanceTime: Optional[str] = None
    startTime: Optional[str] = None
    endTime: Optional[str] = None
    daysBeforeEndTime: Optional[int] = None
    autoRenewalEnabled: Optional[bool] = None
    previousAgreementId: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class AccountBlock(BaseModel):
    """Nested ``detail.acceptor`` / ``detail.proposer`` block."""

    accountId: str = Field(...)
    name: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class OfferBlock(BaseModel):
    """Nested ``detail.offer`` block. ``id`` always present; ``name``
    appears on Amended / Ending / Renewal events."""

    id: str = Field(...)
    name: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class ProductBlock(BaseModel):
    """Nested ``detail.product`` block. Only present on Amended / Ending /
    Renewal / (``RENEW``-intent) Created events; absent on ``NEW`` /
    ``REPLACE`` Created and on Ended."""

    id: str = Field(...)
    title: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class RenewalSummaryBlock(BaseModel):
    """Nested ``detail.renewalSummary`` block. Appears on Amended,
    Ending, Renewal Terms Finalized, and Renewal Upcoming events.

    ``disabledBy`` is ``ACCEPTOR`` / ``PROPOSER`` / ``None``.
    """

    lockoutStartTime: Optional[str] = None
    lockoutReached: Optional[bool] = None
    disabledBy: Optional[str] = None
    tcv: Optional[str] = None
    currency: Optional[str] = None
    termsFinalizedTime: Optional[str] = None
    model_config = ConfigDict(extra="allow")
