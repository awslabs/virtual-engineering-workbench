import typing
from dataclasses import dataclass

from app.packaging.domain.exceptions import domain_exception

# AWS Marketplace offer identifiers come in two shapes surfaced by
# ``marketplace-discovery.GetListing``:
#
# - **Legacy** ``offer-<13 chars>`` (e.g. ``offer-jwqxgu6msev6q``)
# - **New** ``<25 chars>`` base32-like (e.g. ``3cvn2ei0u1ul606g43sdcipsy``)
#
# Both are legitimate offer identifiers accepted by every AWS Marketplace
# API we call (``DescribeEntity``, ``marketplace-agreement``,
# ``CreateAgreementRequest``). AWS never guaranteed a specific format at
# the API level; the legacy prefix was a convention that has now been
# dropped for new offers.
#
# The value object exists to reject obviously-broken inputs at the domain
# boundary (empty strings, whitespace-only, control characters) — NOT to
# enforce a specific format that AWS itself has stopped enforcing. This
# matches the philosophy already established in
# ``agreement_id_value_object`` (see its "test_should_accept_any_non_empty_id"
# rationale).
_MAX_LENGTH = 128


@dataclass(frozen=True)
class OfferIdValueObject:
    """AWS Marketplace Offer identifier.

    Accepts both the legacy ``offer-<13 chars>`` and the new ``<25 chars>``
    formats surfaced by the Marketplace Discovery API. Also permits any
    other non-empty, printable, reasonable-length identifier to avoid a
    trap-door rejection when AWS introduces a third format variant.
    """

    value: str


def from_str(value: typing.Optional[str]) -> OfferIdValueObject:
    if not value:
        raise domain_exception.DomainException("Marketplace offer ID cannot be empty.")
    stripped = value.strip()
    if not stripped:
        raise domain_exception.DomainException("Marketplace offer ID cannot be whitespace.")
    if len(stripped) > _MAX_LENGTH:
        raise domain_exception.DomainException(f"Marketplace offer ID is too long ({len(stripped)} > {_MAX_LENGTH}).")
    # Reject anything with control characters, whitespace inside, or
    # obvious path-traversal / injection markers. AWS offerIds are
    # ASCII-alphanumeric plus '-'; anything else is a caller error.
    if not all(c.isascii() and (c.isalnum() or c == "-") for c in stripped):
        raise domain_exception.DomainException(
            f"Invalid Marketplace offer ID '{value}': " f"expected alphanumeric characters and hyphens only."
        )
    return OfferIdValueObject(value=stripped)
