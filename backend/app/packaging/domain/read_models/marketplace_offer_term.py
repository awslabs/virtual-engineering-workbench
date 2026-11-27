from pydantic import BaseModel, Field


class MarketplaceOfferTerm(BaseModel):
    """A single term attached to a Marketplace Offer, as returned by the
    Discovery API ``GetOfferTerms`` call.

    The Agreements API ``CreateAgreementRequest`` call takes a list of term
    IDs (with optional per-term configuration payloads) that must be a
    subset of the terms surfaced here.

    ``termType`` is the discriminator (e.g.
    ``UsageBasedPricingTerm``, ``ConfigurableUpfrontPricingTerm``,
    ``LegalTerm``, ``SupportTerm``). ``rawTerm`` retains the AWS payload
    verbatim so callers that need to construct term configurations (e.g.
    for annual upfront pricing) do not lose fidelity — no AWS offer term
    variant exposes a human-friendly ``description`` at the top level, so
    the UI must derive its label from ``termType`` + type-specific fields
    in ``rawTerm``.
    """

    termId: str = Field(..., title="TermId")
    termType: str = Field(..., title="TermType")
    rawTerm: dict = Field(default_factory=dict, title="RawTerm")
